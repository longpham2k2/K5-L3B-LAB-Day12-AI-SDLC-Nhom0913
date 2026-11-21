#!/usr/bin/env bash
# AC-P3-06 — smoke Phase 3 (TICKET-03 v1.2): chạy lại được trên commit gắn tag.
#   bash tools/smoke_p3.sh        -> ghi docs/proof/phase-3/{integration,day-smoke,regression-p1-p2}.txt
# Thoát khác 0 nếu có kiểm tra không đạt.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=docs/proof/phase-3
mkdir -p "$OUT"
PY=$(command -v python3 || command -v python)
SEP=$($PY -c "import os; print(os.pathsep)")
export PYTHONUTF8=1
W=$($PY -c 'import tempfile; print(tempfile.mkdtemp().replace("\\", "/"))')
trap 'rm -rf "$W"' EXIT
H="$PY -m chonoi.headless"
REV=$(git rev-parse --short HEAD)$(git diff --quiet HEAD -- chonoi game.contract.json || echo "+dirty")
NOW=$(date -u +%FT%TZ)
FAIL=0
check() {  # check "<mô tả>" <lệnh python trả 0/1>
  if $PY -c "$2"; then echo "ĐẠT  $1"; else echo "KHÔNG ĐẠT  $1"; FAIL=1; fi
}

# ---------- 1. Smoke bàn giao kho cá thể (TICKET-03 mục 1) + từ chối kho đếm ----------
{
  echo "# Smoke bàn giao kho cá thể v1.2 (TICKET-03 mục 1) — $NOW, commit $REV"
  echo '{"gather":{"hold":[{"id":"I1","kind":"ca_linh","fresh":100}],"random_fish":false,"monsters":[]}}' > "$W/dock.json"
  echo '{"frames":[{"tick":0,"interact":true}]}' > "$W/dock-inputs.json"
  echo "--- dock.json"; cat "$W/dock.json"
  echo '$ '"$H"' --mode gather --seed 42 --scenario dock.json --inputs dock-inputs.json --ticks 1 --out gather.jsonl --inventory-out catch.json'
  $H --mode gather --seed 42 --scenario "$W/dock.json" --inputs "$W/dock-inputs.json" --ticks 1 \
     --out "$W/gather.jsonl" --inventory-out "$W/catch.json"; echo "exit=$?"
  echo "--- catch.json"; cat "$W/catch.json"
  echo "--- gather_end"; grep '"gather_end"' "$W/gather.jsonl"
  echo '$ '"$H"' --mode quan --seed 42 --inventory catch.json --ticks 0 --out quan.jsonl'
  $H --mode quan --seed 42 --inventory "$W/catch.json" --ticks 0 --out "$W/quan.jsonl"; echo "exit=$?"
  echo "--- quan snapshot tick 0: stock / bếp / bàn"
  $PY -c 'import json,sys; s=json.loads(open(sys.argv[1], encoding="utf-8").readline()); print("stock", s["stock"]); print("stoves", [x["id"] for x in s["stoves"]]); print("tables", [x["id"] for x in s["tables"]])' "$W/quan.jsonl"

  echo '{"items":{"ca_loc":1}}' > "$W/old_inv.json"
  set +e
  $H --mode quan --seed 42 --inventory "$W/old_inv.json" --ticks 0 --out "$W/bad_q.jsonl" >/dev/null 2>&1
  OLD_RC=$?
  set -e
  echo "old_count_inventory_exit=$OLD_RC"

  echo "--- kiểm tra"
  check "catch.json đúng schema cá thể và fresh chính xác (100 - 0.5/60)" "
import json
items=json.load(open('$W/catch.json', encoding='utf-8'))['items']
ok=len(items)==1 and items[0]['id']=='I1' and items[0]['kind']=='ca_linh' and abs(items[0]['fresh']-(100-0.5/60))<1e-9
raise SystemExit(0 if ok else 1)"
  check "gather_end.inventory == catch.json" "
import json
inv=json.load(open('$W/catch.json', encoding='utf-8'))['items']
ev=[json.loads(l) for l in open('$W/gather.jsonl', encoding='utf-8') if '\"gather_end\"' in l][0]['data']['inventory']['items']
ok=len(inv)==len(ev)==1 and (inv[0]['id'],inv[0]['kind'])==(ev[0]['id'],ev[0]['kind']) and abs(inv[0]['fresh']-ev[0]['fresh'])<0.01
raise SystemExit(0 if ok else 1)"
  check "quan tick 0 nhận đúng id, kind và độ tươi từ catch.json" "
import json
inv=json.load(open('$W/catch.json', encoding='utf-8'))['items']
s=json.loads(open('$W/quan.jsonl', encoding='utf-8').readline())['stock']
ok=len(inv)==len(s)==1 and (inv[0]['id'],inv[0]['kind'])==(s[0]['id'],s[0]['kind']) and abs(inv[0]['fresh']-s[0]['fresh'])<0.01
raise SystemExit(0 if ok else 1)"
  check "file kho đếm v1.1 bị từ chối mã thoát 2" "
import os
raise SystemExit(0 if $OLD_RC == 2 and not os.path.exists('$W/bad_q.jsonl') else 1)"
} > "$OUT/integration.txt" 2>&1
grep -E "^(ĐẠT|KHÔNG ĐẠT)" "$OUT/integration.txt" | sed 's/^/[integration] /'

# ---------- 2. day --days 1, 2 (độ tươi, nấu giá theo tươi, ươn sang Shop, Ngày 2 id mới), 5 ----------
{
  echo "# Smoke --mode day v1.2 (TICKET-03) — $NOW, commit $REV"
  echo; echo "## 2a. day --days 1, không điều khiển: một Ngày tối đa 22.200 tick, chạy <= 20 s"
  START=$($PY -c 'import time; print(time.time())')
  $H --mode day --seed 1 --days 1 --ticks 30000 --snapshot-every 100000 --out "$W/d1.jsonl"; echo "exit=$?"
  $PY -c "import time; print('thời gian chạy: %.2f s' % (time.time()-$START))"
  tail -n 1 "$W/d1.jsonl"
  check "một Ngày = 22.200 tick, days_complete" "
import json; e=json.loads(open('$W/d1.jsonl', encoding='utf-8').readlines()[-1])
raise SystemExit(0 if (e['ticks'],e['reason'],e['days_completed'])==(22200,'days_complete',1) else 1)"
  check "thứ tự đổi pha" "
import json; n=[json.loads(l)['name'] for l in open('$W/d1.jsonl', encoding='utf-8') if '\"type\":\"event\"' in l]
want=['day_start','day_plan','phase_start','gather_end','phase_start','quan_end','phase_start','shop_end']
raise SystemExit(0 if [x for x in n if x in set(want)]==want else 1)"

  echo; echo "## 2b. 2 Ngày: I1(ca_loc, 80) + I2(bong_sung, 30) -> cooked base_price 47, I2 ươn sang Shop, Ngày 2 id mới + oxygen"
  cat > "$W/sc2.json" <<'EOF'
{"day":{"money":200,"earned":200},"gather":{"hold":[{"id":"I1","kind":"ca_loc","fresh":80},{"id":"I2","kind":"bong_sung","fresh":30}],"random_fish":false,"monsters":[]},"quan":{"random_customers":false,"player":{"pos":[2,8]},"time_left_ticks":10,"customers":[{"id":"C1","table_id":"T1","dish_id":"ca_loc_nuong_trui","order_tick":0}]}}
EOF
  echo '{"frames":[{"tick":0,"interact":true},{"tick":1,"interact":false},{"tick":2,"interact":true},{"tick":11,"interact":false,"buy":"oxygen","shop_done":true}]}' > "$W/in2.json"
  $H --mode day --seed 1 --days 2 --scenario "$W/sc2.json" --inputs "$W/in2.json" --ticks 30000 --snapshot-every 1 --out "$W/d2.jsonl"; echo "exit=$?"
  grep -E '"name":"(spoiled|cook_started|bought|shop_end|day_start)"|"type":"end"' "$W/d2.jsonl"
  check "nấu chốt giá 47k và item I1 cá thể" "
import json
evs=[json.loads(l) for l in open('$W/d2.jsonl', encoding='utf-8') if '\"cook_started\"' in l]
d=evs[0]['data']
ok=d['base_price']==47 and len(d['items'])==1 and d['items'][0]['id']=='I1' and d['items'][0]['kind']=='ca_loc'
raise SystemExit(0 if ok else 1)"
  check "Shop giữ I2 ươn; Ngày 2 cấp id mới I3/I4 và áp oxygen 2700" "
import json
s={r['tick']:r for r in map(json.loads,open('$W/d2.jsonl', encoding='utf-8')) if r['type']=='snapshot'}
sp=[json.loads(l) for l in open('$W/d2.jsonl', encoding='utf-8') if '\"spoiled\"' in l]
shop_ok=s[11]['phase']=='shop' and len(s[11]['stock'])==1 and s[11]['stock'][0]['id']=='I2' and s[11]['stock'][0]['fresh']<30
day2_ok=s[12]['day']==2 and s[12]['active_upgrades']=={'oxygen':1} and s[12]['player']['oxygen_max_ticks']==2700 and [(x['id'],x['kind'],x['fresh']) for x in s[12]['hold']]==[('I3','ca_loc',80.0),('I4','bong_sung',30.0)]
sp_ok=[(e['day'],e['data']['item_id']) for e in sp[:2]]==[(1,'I2'),(2,'I4')]
raise SystemExit(0 if shop_ok and day2_ok and sp_ok else 1)"

  echo; echo "## 2c. 5 Ngày: kế hoạch D1–D5 và tất định byte"
  $H --mode day --seed 1 --days 5 --ticks 200000 --snapshot-every 1000000 --out "$W/d5.jsonl"; echo "exit=$?"
  tail -n 1 "$W/d5.jsonl"
  check "D1–D5 đúng bảng PRD" "
import json; rows=[json.loads(l) for l in open('$W/d5.jsonl', encoding='utf-8')]; got=[r['data'] for r in rows if r['type']=='event' and r['name']=='day_plan']
want=[{'ca_loc':3,'bong_sung':6},{'ca_loc':2,'ca_linh':6,'bong_dien_dien':2},
      {'bong_sung':4,'ca_loc':2,'bong_dien_dien':2,'ca_keo':4},
      {'ca_linh':2,'ca_keo':1,'keo_neo':1,'bong_dien_dien':1,'ca_loc':2,'bong_sung':2},
      {'ca_linh':5,'ca_keo':1,'keo_neo':1,'bong_dien_dien':2,'ca_loc':1}]
raise SystemExit(0 if [g['ingredients'] for g in got]==want and len(got)==5 else 1)"
  check "5 Ngày: days_completed 5, ticks 5 x 22.200" "
import json; e=json.loads(open('$W/d5.jsonl', encoding='utf-8').readlines()[-1])
raise SystemExit(0 if (e['days_completed'],e['ticks'],e['reason'])==(5,111000,'days_complete') else 1)"
  check "tất định: cùng seed -> JSONL giống từng byte" "
import subprocess,sys,filecmp
subprocess.run([sys.executable,'-m','chonoi.headless','--mode','day','--seed','1','--days','1','--ticks','30000','--snapshot-every','100000','--out','$W/d1b.jsonl'],check=True)
raise SystemExit(0 if filecmp.cmp('$W/d1.jsonl','$W/d1b.jsonl',shallow=False) else 1)"
} > "$OUT/day-smoke.txt" 2>&1
grep -E "^(ĐẠT|KHÔNG ĐẠT)" "$OUT/day-smoke.txt" | sed 's/^/[day] /'

# ---------- 3. Regression P1 + P2 + P3 ----------
{
  echo "# Regression P1–P2 với số chuẩn v1.2 — $NOW, commit $REV"
  echo "# Test cũ đổi vì luật v1.2 (kho cá thể, giữ theo id, giá theo tươi): ghi rõ trong test và CHANGELOG.md."
  PYTHONPATH="tests${SEP}." $PY -m unittest \
    tests.test_python_starter_units tests.test_smoke_p1 tests.test_gather_slice1 tests.test_gather_slice2 \
    tests.test_gather_fish_p2 tests.test_gather_monsters_p2 tests.test_quan_slice3 tests.test_quan_slice4 \
    tests.test_p2_quan_shop tests.test_day_and_pause tests.test_live tests.test_team_check 2>&1 | tail -4
  echo; echo "# Toàn bộ bộ test (P1 + P2 + P3)"
  PYTHONPATH="tests${SEP}." $PY -m unittest discover -s tests 2>&1 | tail -3
} > "$OUT/regression-p1-p2.txt" 2>&1
grep -E "^(OK|FAILED|Ran)" "$OUT/regression-p1-p2.txt" | sed 's/^/[regression] /'
grep -q "FAILED" "$OUT/regression-p1-p2.txt" && FAIL=1

exit $FAIL
