# Forza Horizon 6 — UDP Telemetry Packet Format

**Total packet size: 324 bytes.** Data is only sent while the player is actively driving (not during menus, pauses, replays, rewinds, or after finishing). One-way UDP output only — the game receives nothing.

FH6 includes three fields not in Forza Motorsport: `CarGroup`, `SmashableVelDiff`, and `SmashableMass` (inserted after `NumCylinders`, before `PositionX`). FH6 does **not** include `TireWear` or `TrackOrdinal`.

## Type Legend

| Notation | Meaning |
| -------- | ------- |
| `S32` | Signed 32-bit integer |
| `U32` | Unsigned 32-bit integer |
| `F32` | 32-bit float |
| `U16` | Unsigned 16-bit integer |
| `U8` | Unsigned 8-bit integer |
| `S8` | Signed 8-bit integer |

## Packet Fields (in order)

```text
S32  IsRaceOn                          // 1 = race on, 0 = menus/stopped
U32  TimestampMS                       // can overflow to 0

F32  EngineMaxRpm
F32  EngineIdleRpm
F32  CurrentEngineRpm

// Car local space: X=right, Y=up, Z=forward
F32  AccelerationX / Y / Z
F32  VelocityX / Y / Z
F32  AngularVelocityX / Y / Z          // rad/s: X=pitch, Y=yaw, Z=roll

F32  Yaw / Pitch / Roll                // car orientation (radians)

// Suspension travel normalized: 0.0=max stretch, 1.0=max compression
F32  NormalizedSuspensionTravelFrontLeft / FrontRight / RearLeft / RearRight

// Tire slip ratio: 0=100% grip, |ratio|>1.0=loss of grip
F32  TireSlipRatioFrontLeft / FrontRight / RearLeft / RearRight

F32  WheelRotationSpeedFrontLeft / FrontRight / RearLeft / RearRight  // rad/s

S32  WheelOnRumbleStripFrontLeft / FrontRight / RearLeft / RearRight  // 1=on strip
S32  WheelInPuddleFrontLeft / FrontRight / RearLeft / RearRight       // 1=in puddle

F32  SurfaceRumbleFrontLeft / FrontRight / RearLeft / RearRight       // for force feedback

// Tire slip angle: 0=100% grip, |angle|>1.0=loss of grip
F32  TireSlipAngleFrontLeft / FrontRight / RearLeft / RearRight

// Tire combined slip: 0=100% grip, |slip|>1.0=loss of grip
F32  TireCombinedSlipFrontLeft / FrontRight / RearLeft / RearRight

F32  SuspensionTravelMetersFrontLeft / FrontRight / RearLeft / RearRight  // actual meters

S32  CarOrdinal                        // unique car make/model ID
S32  CarClass                          // 0 (D) to 7 (X)
S32  CarPerformanceIndex               // 100 (worst) to 999 (best)
S32  DrivetrainType                    // 0=FWD, 1=RWD, 2=AWD
S32  NumCylinders

// FH6-exclusive fields (not in Forza Motorsport)
U32  CarGroup
F32  SmashableVelDiff                  // velocity loss from smashable collision (m/s)
F32  SmashableMass                     // mass of hit smashable object (kg)

F32  PositionX / Y / Z                 // world space (meters)
F32  Speed                             // m/s
F32  Power                             // watts
F32  Torque                            // newton-meters

F32  TireTempFrontLeft / FrontRight / RearLeft / RearRight

F32  Boost                             // PSI above atmospheric
F32  Fuel                              // 0.0=empty, 1.0=full
F32  DistanceTraveled                  // meters

F32  BestLap                           // seconds; 0.0 if N/A
F32  LastLap
F32  CurrentLap
F32  CurrentRaceTime                   // seconds since driving started

U16  LapNumber
U8   RacePosition

U8   Accel                             // 0–255
U8   Brake
U8   Clutch
U8   HandBrake

U8   Gear

S8   Steer                             // -127=full left, 0=center, 127=full right
S8   NormalizedDrivingLine             // -127 to 127
S8   NormalizedAIBrakeDifference       // -127 to 127
```
