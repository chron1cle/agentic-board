Migrate the existing sensor utility from sensor_legacy.py to the bundled
sensor_v2.py API. Keep sensor_v2.py and sensor_legacy.py intact. Update the
CLI and both modules, preserving their public names and signatures. No
application file may import sensor_legacy.

app.py reads JSON Lines objects {"records":{key:[integer,unit]|"offline"},
"keys":[...]}. Output one object with rows, total_milli and calls.
The rows list has one item per key in request order, including duplicates.
reader.collect(sensor,key) returns {"id":key,"status":"ok","milli":integer}
for recognized units whole or milli. Convert whole units to thousandths.
Return {"id":key,"status":STATUS} for missing, offline, or invalid unit.
aggregate.report(sensor,keys) returns the rows, sum of successful values,
and the sensor's calls list. Fetch once per requested key, in order.
Standard library only.
