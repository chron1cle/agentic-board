`logs/app.log` is one day of traffic from the edge proxy. Read it and write a
file named `report.json` in the project root (next to the `logs` directory)
containing exactly these six keys:

| key                | meaning                                                        |
| ------------------ | -------------------------------------------------------------- |
| `errors`           | how many log lines have level `ERROR`                          |
| `unique_error_ips` | how many distinct client IPs appear on those `ERROR` lines     |
| `worst_ip`         | the client IP with the most `ERROR` lines                      |
| `worst_count`      | how many `ERROR` lines that IP has                             |
| `slowest_ms`       | the largest latency in milliseconds anywhere in the file       |
| `slowest_path`     | the request path of that single slowest line                   |

Every value is a JSON number except `worst_ip` and `slowest_path`, which are
strings. If several IPs tie for most errors, pick the one that sorts first as a
string.

Do not edit the log file itself.
