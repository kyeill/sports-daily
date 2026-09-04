import datetime
from zoneinfo import ZoneInfo
import sports_daily, filters
cfg = sports_daily.load_config(None)
tz = ZoneInfo(cfg.get('timezone', 'America/New_York'))
today = sports_daily.parse_day(None, tz)
real = filters._final_margin
for offset in range(-6, 3):
    d = today + datetime.timedelta(days=offset)
    filters._final_margin = lambda g: None          # old behaviour
    before = {g['id'] for g in sports_daily.collect(cfg, d, tz)[0]}
    filters._final_margin = real                    # new behaviour
    after = {g['id'] for g in sports_daily.collect(cfg, d, tz)[0]}
    dropped = before - after
    added = after - before
    flag = ''
    if added: flag = '  !! ADDED %d' % len(added)
    print('%s (%+d): %3d -> %3d   dropped %d%s'
          % (d, offset, len(before), len(after), len(dropped), flag))
