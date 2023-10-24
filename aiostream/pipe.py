"""Gather the pipe operators."""
from __future__ import annotations

from . import stream

accumulate = stream.accumulate.pipe
action = stream.action.pipe
amap = stream.amap.pipe
chain = stream.chain.pipe
chunks = stream.chunks.pipe
concat = stream.concat.pipe
concatmap = stream.concatmap.pipe
cycle = stream.cycle.pipe
delay = stream.delay.pipe
dropwhile = stream.dropwhile.pipe
enumerate = stream.enumerate.pipe
filter = stream.filter.pipe
flatmap = stream.flatmap.pipe
flatten = stream.flatten.pipe
getitem = stream.getitem.pipe
list = stream.list.pipe
map = stream.map.pipe
merge = stream.merge.pipe
print = stream.print.pipe
reduce = stream.reduce.pipe
skip = stream.skip.pipe
skiplast = stream.skiplast.pipe
smap = stream.smap.pipe
spaceout = stream.spaceout.pipe
starmap = stream.starmap.pipe
switch = stream.switch.pipe
switchmap = stream.switchmap.pipe
take = stream.take.pipe
takelast = stream.takelast.pipe
takewhile = stream.takewhile.pipe
timeout = stream.timeout.pipe
until = stream.until.pipe
zip = stream.zip.pipe
ziplatest = stream.ziplatest.pipe
