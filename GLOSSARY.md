# Football scouting

This glossary defines the scouting language used to describe players in the project's event-data sample.

## Scouting concepts

**Scouting profile**:
A role-specific view that defines its candidate pool and the evidence used to compare players.
_Avoid_: Universal ranking, overall player score

**Role share**:
The share of a player's season minutes assigned to appearances whose primary position matches a profile's role pool; it approximates role time when a player changes position during an appearance.
_Avoid_: Exact position minutes

**Progressive action**:
A pass or carry whose recorded end location advances the ball at least 10 StatsBomb x-coordinate units toward the attacking goal.
_Avoid_: Progression score

**Shot assist**:
A pass marked by StatsBomb as directly leading to a shot; it is an event flag, not an expected-assist value.
_Avoid_: xA

**Expected goals (xG)**:
A source-provided estimate of the likelihood that a recorded shot becomes a goal, attached to that shot.
_Avoid_: Project-trained finishing score
