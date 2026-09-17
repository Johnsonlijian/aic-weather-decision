# Operation contract and evidence ceiling

The current engine has a single fully documented threshold fixture: the HS2
launch-girder segment operation. The HS2 Learning Legacy account records a
start prohibition above 11.1 m/s gust and permits an operation already in
progress to continue up to 20 m/s; it also records that the operation is a
three-day girder launch between piers, but it does not provide a defensible
segment-level execution duration or a complete response rule above 20 m/s.
The implementation therefore uses 11.1/20.0 only for threshold and
state-transition tests. Its two-slot test duration is explicitly abstract and
is not presented as a field production rate.

KNMI FX is a past-hour maximum observation. NOAA GFS GUST in the downloaded
probe is an instantaneous gridded forecast field. These variables are retained
as different columns. A forecast-to-observation calibration and a conservative
availability rule must be frozen before any operational-looking performance
claim. The PSPLIB and DSLIB networks retain abstract or source-native time
units; attaching them to weather hours is a separate experimental assumption.

This contract closes the software's threshold and state semantics for the
constructed tests. It does not close the empirical calibration, field
duration, interruption/recourse, or journal submission gates.
