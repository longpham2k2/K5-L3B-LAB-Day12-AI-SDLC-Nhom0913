#!/usr/bin/env bash
# AC-P2-09 — smoke Phase 2 (TICKET-02 mục 5): chạy lại được trên commit gắn tag.
#   bash tools/smoke_p2.sh        -> ghi docs/proof/phase-2/{integration,day-smoke,regression-p1}.txt
# Thoát khác 0 nếu có kiểm tra không đạt.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=docs/proof/phase-2
mkdir -p "$OUT"
W=$(mktemp -d)
trap 'rm -rf "$W"' EXIT
H="python3 -m chonoi.headless"
REV=$(git rev-parse --short HEAD)$(git diff --quiet HEAD -- chonoi game.contract.json || echo "+dirty")
NOW=$(date -u +%FT%TZ)
FAIL=0
check() {  # check "<mô tả>" <lệnh python trả 0/1>
  if python3 -c "$2"; then echo "ĐẠT  $1"; else echo "KHÔNG ĐẠT  $1"; FAIL=1; fi
}

# ---------- 1. Tích hợp gather --inventory-out -> quan --inventory (số chuẩn v1.1) ----------
{
  echo "# Smoke tích hợp hai tiến trình (TICKET-02 mục 5, phút 20) — $NOW, commit $REV"
  echo "# Giỏ dùng cả 2 nguyên liệu mới (ca_keo, keo_neo); cập bến ở tick 0."
  echo '{"gather":{"hold":["ca_loc","bong_sung","bong_sung","ca_keo","ca_keo","keo_neo"],"random_fish":false}}' > "$W/dock.json"
  echo '{"frames":[{"tick":0,"interact":true}]}' > "$W/dock-inputs.json"
  echo "--- dock.json"; cat "$W/dock.json"
  echo '$ '"$H"' --mode gather --seed 42 --scenario dock.json --inputs dock-inputs.json --ticks 1 --out gather.jsonl --inventory-out catch.json'
  $H --mode gather --seed 42 --scenario "$W/dock.json" --inputs "$W/dock-inputs.json" --ticks 1 \
     --out "$W/gather.jsonl" --inventory-out "$W/catch.json"; echo "exit=$?"
  echo "--- catch.json"; cat "$W/catch.json"
  echo "--- gather_end"; grep '"gather_end"' "$W/gather.jsonl"
  echo '$ '"$H"' --mode quan --seed 42 --inventory catch.json --ticks 1200 --snapshot-every 100000 --out quan.jsonl'
  $H --mode quan --seed 42 --inventory "$W/catch.json" --ticks 1200 --snapshot-every 100000 --out "$W/quan.jsonl"; echo "exit=$?"
  echo "--- quan snapshot tick 0: stock / bếp / bàn"
  python3 -c 'import json,sys; s=json.loads(open(sys.argv[1]).readline()); print("stock", s["stock"]); print("stoves", [x["id"] for x in s["stoves"]]); print("tables", [x["id"] for x in s["tables"]])' "$W/quan.jsonl"
  echo "--- khách (lọc 6 món theo kho khả dụng)"; grep '"customer_arrived"\|"no_dish"' "$W/quan.jsonl"
  echo "--- kiểm tra"
  check "kho quán tick 0 == file kho gather ghi" "
import json; inv=json.load(open('$W/catch.json'))['items']; s=json.loads(open('$W/quan.jsonl').readline())
raise SystemExit(0 if s['stock']==inv=={'bong_sung':2,'ca_keo':2,'ca_loc':1,'keo_neo':1} else 1)"
  check "gather_end.inventory == file kho" "
import json; inv=json.load(open('$W/catch.json'))
ev=[json.loads(l) for l in open('$W/gather.jsonl') if '\"gather_end\"' in l][0]
raise SystemExit(0 if ev['data']['inventory']==inv else 1)"
  check "quán có B1,B2 và T1–T4" "
import json; s=json.loads(open('$W/quan.jsonl').readline())
raise SystemExit(0 if [x['id'] for x in s['stoves']]==['B1','B2'] and [x['id'] for x in s['tables']]==['T1','T2','T3','T4'] else 1)"
} > "$OUT/integration.txt" 2>&1
grep -E "^(ĐẠT|KHÔNG ĐẠT)" "$OUT/integration.txt" | sed 's/^/[integration] /'

# ---------- 2. day --days 1, nhiều Ngày, D1–D5 ----------
{
  echo "# Smoke --mode day (TICKET-02 mục 5, phút 35–45) — $NOW, commit $REV"
  echo; echo "## 2a. day --days 1, không điều khiển: một Ngày tối đa 22.200 tick, chạy ≤ 20 s"
  START=$(python3 -c 'import time; print(time.time())')
  $H --mode day --seed 1 --days 1 --ticks 30000 --snapshot-every 100000 --out "$W/d1.jsonl"; echo "exit=$?"
  python3 -c "import time; print('thời gian chạy: %.2f s' % (time.time()-$START))"
  grep -E '"name":"(day_start|day_plan|phase_start|gather_end|quan_end|shop_end)"|"type":"end"' "$W/d1.jsonl"
  check "một Ngày = 22.200 tick, days_complete" "
import json; e=json.loads(open('$W/d1.jsonl').readlines()[-1])
raise SystemExit(0 if (e['ticks'],e['reason'],e['days_completed'])==(22200,'days_complete',1) else 1)"
  check "thứ tự đổi pha" "
import json; n=[json.loads(l)['name'] for l in open('$W/d1.jsonl') if '\"type\":\"event\"' in l]
want=['day_start','day_plan','phase_start','gather_end','phase_start','quan_end','phase_start','shop_end']
raise SystemExit(0 if [x for x in n if x in set(want)]==want else 1)"

  echo; echo "## 2b. 2 Ngày: có 200 tiền, cập bến ngay, mua oxygen trong Shop Ngày 1 -> áp dụng từ Ngày 2"
  echo '{"day":{"money":200,"earned":200},"gather":{"random_fish":false}}' > "$W/sc2.json"
  echo '{"frames":[{"tick":0,"interact":true},{"tick":1,"interact":false},{"tick":10802,"buy":"oxygen"},{"tick":10803,"buy":"oxygen"},{"tick":10804,"shop_done":true}]}' > "$W/in2.json"
  echo "--- scenario"; cat "$W/sc2.json"; echo "--- inputs"; cat "$W/in2.json"
  $H --mode day --seed 1 --days 2 --scenario "$W/sc2.json" --inputs "$W/in2.json" --ticks 40000 --snapshot-every 1 --out "$W/d2.jsonl"; echo "exit=$?"
  grep -E '"name":"(bought|buy_failed|shop_end|day_start)"|"type":"end"' "$W/d2.jsonl"
  python3 -c '
import json,sys
rows=[json.loads(l) for l in open(sys.argv[1])]
for r in rows:
    if r["type"]=="snapshot" and r["tick"] in (10803, 10805, 10806):
        p=r.get("player",{})
        print("snapshot tick", r["tick"], r["phase"], "day", r["day"], "upgrades", r["upgrades"], "active", r["active_upgrades"], "oxy_max", p.get("oxygen_max_ticks"))' "$W/d2.jsonl"
  check "mua cấp 1 trừ money, giữ earned; lần 2 thiếu tiền -> buy_failed funds" "
import json; ev=[json.loads(l) for l in open('$W/d2.jsonl') if '\"type\":\"event\"' in l]
b=[e['data'] for e in ev if e['name']=='bought']; f=[e['data'] for e in ev if e['name']=='buy_failed']
raise SystemExit(0 if b==[{'upgrade':'oxygen','level':1,'price':200,'money':0}] and f==[{'action':'oxygen','reason':'funds'}] else 1)"
  check "cấp mua hiện ngay, chỉ áp dụng (oxy 2700) từ Ngày 2" "
import json; s={r['tick']:r for r in map(json.loads,open('$W/d2.jsonl')) if r['type']=='snapshot'}
a=s[10803]; b=s[10806]
ok=a['upgrades']=={'oxygen':1} and a['active_upgrades']=={} and b['day']==2 and b['active_upgrades']=={'oxygen':1} and b['player']['oxygen_max_ticks']==2700
raise SystemExit(0 if ok else 1)"
  check "end: earned giữ 200, days_completed 2" "
import json; e=json.loads(open('$W/d2.jsonl').readlines()[-1])
raise SystemExit(0 if (e['money'],e['earned'],e['days_completed'],e['reason'])==(0,200,2,'days_complete') else 1)"

  echo; echo "## 2c. 5 Ngày: kế hoạch D1–D5 công bố đúng (so với TICKET-02 mục 2)"
  $H --mode day --seed 1 --days 5 --ticks 200000 --snapshot-every 1000000 --out "$W/d5.jsonl"; echo "exit=$?"
  grep '"name":"day_plan"' "$W/d5.jsonl"; tail -1 "$W/d5.jsonl"
  check "D1–D5 đúng bảng PRD" "
import json; rows=[json.loads(l) for l in open('$W/d5.jsonl')]; got=[r['data'] for r in rows if r['type']=='event' and r['name']=='day_plan']
want=[{'ca_loc':3,'bong_sung':6},{'ca_loc':2,'ca_linh':6,'bong_dien_dien':2},
      {'bong_sung':4,'ca_loc':2,'bong_dien_dien':2,'ca_keo':4},
      {'ca_linh':2,'ca_keo':1,'keo_neo':1,'bong_dien_dien':1,'ca_loc':2,'bong_sung':2},
      {'ca_linh':5,'ca_keo':1,'keo_neo':1,'bong_dien_dien':2,'ca_loc':1}]
raise SystemExit(0 if [g['ingredients'] for g in got]==want and len(got)==5 else 1)"
  check "5 Ngày: days_completed 5, ticks 5 × 22.200" "
import json; e=json.loads(open('$W/d5.jsonl').readlines()[-1])
raise SystemExit(0 if (e['days_completed'],e['ticks'],e['reason'])==(5,111000,'days_complete') else 1)"
  check "tất định: cùng seed -> JSONL giống từng byte" "
import subprocess,filecmp
subprocess.run('$H --mode day --seed 1 --days 1 --ticks 30000 --snapshot-every 100000 --out $W/d1b.jsonl'.split(),check=True)
raise SystemExit(0 if filecmp.cmp('$W/d1.jsonl','$W/d1b.jsonl',shallow=False) else 1)"
} > "$OUT/day-smoke.txt" 2>&1
grep -E "^(ĐẠT|KHÔNG ĐẠT)" "$OUT/day-smoke.txt" | sed 's/^/[day] /'

# ---------- 3. Regression P1 với số chuẩn v1.1 ----------
{
  echo "# Regression P1 với số chuẩn v1.1 — $NOW, commit $REV"
  echo "# Test P1 đã đổi vì luật mới (có ghi lý do trong test và commit): 6->8 đàn đầu ca; attack là nút hợp lệ; --mode day được hỗ trợ."
  PYTHONPATH=tests:. python3 -m unittest tests.test_smoke_p1 tests.test_gather_slice1 tests.test_gather_slice2 \
    tests.test_quan_slice3 tests.test_quan_slice4 -v 2>&1 | tail -4
  echo; echo "# Toàn bộ bộ test"
  PYTHONPATH=tests:. python3 -m unittest discover -s tests 2>&1 | tail -3
} > "$OUT/regression-p1.txt" 2>&1
grep -E "^(OK|FAILED|Ran)" "$OUT/regression-p1.txt" | sed 's/^/[regression] /'
grep -q "FAILED" "$OUT/regression-p1.txt" && FAIL=1

exit $FAIL
