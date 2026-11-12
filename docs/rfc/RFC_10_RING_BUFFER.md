# RFC-10: MQTT v5 Telemetry Buffer

- Data Structure: Lock-free ring buffer in shared memory
- Compaction: Dynamic downsampling of low-priority telemetry
- Resilience: 100% telemetry retention during 15-minute network outages