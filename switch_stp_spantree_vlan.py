# Pyhton STP Monitoring Script
#
# Monitors STP activity for a configurable time period.
# Detects:
#   - Root Bridge changes
#   - Count-To-Infinity (CTI) events
#   - Priority Mismatch events
#   - RSTP CTI activation events
#
# Collects:
#   - VLAN statistics
#   - Root Priority
#   - Root MAC
#   - Port statistics
#   - Root Priority transitions
#   - Root change timeline
#
# Generates a summary report and restores STP logging
# to INFO level when the monitoring period is completed.
#
# Start:
# python3 /flash/python/switch_stp_spantree_vlan.py
#
#!/usr/bin/python3


import os
import re
import time
import subprocess
from datetime import datetime

LOGFILE = "/flash/stp_monitoring.log"
SWLOG = "/flash/swlog_chassis1"

RUNTIME = 300
POLL_INTERVAL = 10

last_position = 0

vlan_stats = {}
port_stats = {}

root_timeline = []
priority_transitions = []

cti_events = 0
priority_mismatch_events = 0
rstp_cti_events = 0

spantree_before = {}
spantree_after = {}


def timestamp():

    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def log(msg):

    print(msg)

    try:

        with open(LOGFILE, "a") as f:

            f.write(msg + "\n")
            f.flush()

    except:
        pass


def run_command(cmd):

    try:

        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        stdout, stderr = proc.communicate()

        return stdout.decode(
            "utf-8",
            errors="ignore"
        )

    except:

        return ""


def enable_debug():

    os.system(
        "swlog appid stpni subapp all level debug1"
    )

    os.system(
        "swlog appid stpcmm subapp all level debug1"
    )

    log(
        "[%s] STP DEBUG ENABLED"
        % timestamp()
    )


def disable_debug():

    os.system(
        "swlog appid stpni subapp all level info"
    )

    os.system(
        "swlog appid stpcmm subapp all level info"
    )

    log(
        "[%s] STP DEBUG DISABLED"
        % timestamp()
    )


def get_stp_vlans():

    vlans = []

    output = run_command(
        "show spantree"
    )

    for line in output.splitlines():

        m = re.match(
            r"\s*(\d+)\s+ON",
            line
        )

        if m:

            vlans.append(
                m.group(1)
            )

    return vlans


def parse_spantree_vlan(output):

    data = {}

    patterns = {

        "priority":
        r"Priority\s*:\s*([0-9]+)",

        "bridge_id":
        r"Bridge ID\s*:\s*(.+)",

        "designated_root":
        r"Designated Root\s*:\s*(.+)",

        "root_port":
        r"Root Port\s*:\s*(.+)",

        "topology_changes":
        r"Topology Changes\s*:\s*([0-9]+)",

        "last_tc_port":
        r"Last TC Rcvd Port\s*:\s*(.+)",

        "last_tc_bridge":
        r"Last TC Rcvd Bridge\s*:\s*(.+)"
    }

    for key, pattern in patterns.items():

        m = re.search(
            pattern,
            output
        )

        if m:

            data[key] = m.group(1).strip().rstrip(",")

        else:

            data[key] = "unknown"

    return data


def capture_snapshot():

    result = {}

    for vlan in get_stp_vlans():

        output = run_command(
            "show spantree vlan %s"
            % vlan
        )

        result[vlan] = parse_spantree_vlan(
            output
        )

    return result


def read_new_lines():

    global last_position

    try:

        with open(SWLOG, "r") as f:

            f.seek(last_position)

            lines = f.readlines()

            last_position = f.tell()

            return lines

    except:

        return []


def update_vlan(vlan):

    if vlan not in vlan_stats:

        vlan_stats[vlan] = {

            "root_changes": 0,
            "root_priority": "unknown",
            "root_mac": "unknown"

        }


def update_port(port):

    if port not in port_stats:

        port_stats[port] = 0

    port_stats[port] += 1


def process_line(line):

    global cti_events
    global priority_mismatch_events
    global rstp_cti_events

    vlan = None

    vlan_match = re.search(
        r"vid=(\d+)",
        line
    )

    if vlan_match:

        vlan = vlan_match.group(1)

        update_vlan(vlan)

    port_match = re.search(
        r"port(?:id)?=x([0-9A-Fa-f]+)",
        line
    )

    if port_match:

        update_port(
            "x" + port_match.group(1)
        )

    root_match = re.search(
        r"ROOT ([0-9A-Fa-f]+): ([0-9A-Fa-f:]+)",
        line
    )

    if root_match and vlan:

        vlan_stats[vlan]["root_priority"] = (
            root_match.group(1)
        )

        vlan_stats[vlan]["root_mac"] = (
            root_match.group(2)
        )

    if "Count To Infinity detected" in line:

        cti_events += 1

    if "MisMatch Priority" in line:

        priority_mismatch_events += 1

    if "RSTP CTI Activation Message Sent" in line:
        rstp_cti_events += 1

    if "IN-BPDU-Root_Bridge_Priority" in line:
        p = re.search(
            r"IN-BPDU-Root_Bridge_Priority=([0-9]+).*Current Root_Bridge_Priority *=([0-9]+)",
            line
        )

        if p:

            old_prio = p.group(2)
            new_prio = p.group(1)

            if vlan is None:

                vlan = "unknown"

            root_mac = vlan_stats.get(
                vlan,
                {}
            ).get(
                "root_mac",
                "unknown"
            )

            bridge_id = "unknown"

            if vlan in spantree_before:

                bridge_id = spantree_before[vlan].get(
                    "bridge_id",
                    "unknown"
                )

            priority_transitions.append({

                "time": timestamp(),
                "vlan": vlan,
                "old_priority": old_prio,
                "new_priority": new_prio,
                "root_mac": root_mac,
                "bridge_id": bridge_id

            })
    if "Bridge has become new Root" in line:

        m = re.search(
            r"instance (\d+)",
            line
        )

        vlan = "unknown"

        if m:

            vlan = m.group(1)

        update_vlan(vlan)

        vlan_stats[vlan][
            "root_changes"
        ] += 1

        root_timeline.append({

            "time": timestamp(),

            "vlan": vlan

        })

        log("")
        log("=" * 60)
        log("ROOT CHANGE DETECTED")
        log(line.strip())
        log("=" * 60)


def process_lines(lines):

    stp_lines = 0

    for line in lines:

        if "stp" not in line.lower():

            continue

        stp_lines += 1

        process_line(line)

    log(
        "[%s] Read %s STP lines"
        % (
            timestamp(),
            stp_lines
        )
    )


def print_summary():

    log("")
    log("=" * 60)
    log("STP MONITORING SUMMARY")
    log("=" * 60)

    total_changes = 0

    for vlan in sorted(
        vlan_stats.keys()
    ):

        data = vlan_stats[vlan]

        total_changes += data[
            "root_changes"
        ]

        log("")
        log("VLAN %s" % vlan)
        log("Root Changes : %s" % data["root_changes"])
        log("Root Priority : %s" % data["root_priority"])
        log("Root MAC : %s" % data["root_mac"])

    log("")
    log("=" * 60)
    log("SNAPSHOT COMPARISON")
    log("=" * 60)

    for vlan in sorted(
        spantree_before.keys()
    ):

        before = spantree_before[vlan]
        after = spantree_after[vlan]

        try:

            tc_delta = (

                int(after["topology_changes"])

                -

                int(before["topology_changes"])

            )

        except:

            tc_delta = "unknown"

        log("")
        log("VLAN %s" % vlan)

        if (
            after["bridge_id"]
            ==
            after["designated_root"]
        ):

            role = "ROOT BRIDGE"

        else:

            role = "NON ROOT BRIDGE"

        log("Role : %s" % role)

        log(
            "Priority : %s"
            % after["priority"]
        )

        log(
            "Root Port : %s"
            % after["root_port"]
        )

        log(
            "Topology Changes : %s -> %s (Delta=%s)"
            % (
                before["topology_changes"],
                after["topology_changes"],
                tc_delta
            )
        )

        log(
            "Last TC Port : %s"
            % after["last_tc_port"]
        )

        log(
            "Last TC Bridge : %s"
            % after["last_tc_bridge"]
        )

    log("")
    log("=" * 60)
    log("STP ANOMALIES")
    log("=" * 60)

    log(
        "Count To Infinity Events : %s"
        % cti_events
    )

    log(
        "Priority Mismatch Events : %s"
        % priority_mismatch_events
    )

    log(
        "RSTP CTI Events : %s"
        % rstp_cti_events
    )

    log("")
    log("=" * 60)
    log("ROOT PRIORITY CHANGES")
    log("=" * 60)

    if len(priority_transitions) == 0:

        log("No priority changes detected")

    else:

        for item in priority_transitions:

            log("")

            log(
                "Time       : %s"
                % item["time"]
            )

            log(
                "VLAN       : %s"
                % item["vlan"]
            )

            log(
                "Bridge ID  : %s"
                % item["bridge_id"]
            )

            log(
                "Priority   : %s -> %s"
                % (
                    item["old_priority"],
                    item["new_priority"]
                )
            )

            log(
                "Root MAC   : %s"
                % item["root_mac"]
            )

            log("-" * 60)

    log("")
    log("=" * 60)
    log("PORT STATISTICS")
    log("=" * 60)

    sorted_ports = sorted(

        port_stats.items(),

        key=lambda x: x[1],

        reverse=True

    )

    for port, count in sorted_ports:

        try:

            p = int(
                port.replace("x", "")
            ) + 1

            port_name = (
                "1/1/%s"
                % p
            )

        except:

            port_name = port

        log(
            "%s : %s events"
            % (
                port_name,
                count
            )
        )

    log("")
    log("=" * 60)
    log("ROOT CHANGE TIMELINE")
    log("=" * 60)

    for entry in root_timeline:

        log(
            "%s VLAN=%s"
            % (
                entry["time"],
                entry["vlan"]
            )
        )

    log("")
    log(
        "TOTAL ROOT CHANGES : %s"
        % total_changes
    )


def main():

    global last_position
    global spantree_before
    global spantree_after

    log("")
    log("=" * 60)

    log(
        f"STP monitoring script is running for {RUNTIME // 60} min."
    )

    log("=" * 60)

    enable_debug()

    log(
        "Collecting STP baseline ..."
    )

    spantree_before = (
        capture_snapshot()
    )

    try:

        last_position = os.path.getsize(
            SWLOG
        )

    except:

        last_position = 0

    start_time = time.time()

    while True:

        uptime = int(
            time.time()
            - start_time
        )

        log(
            "[%s] Script running. Uptime=%s sec"
            % (
                timestamp(),
                uptime
            )
        )

        process_lines(
            read_new_lines()
        )

        if uptime >= RUNTIME:

            log(
                "Collecting final STP snapshot ..."
            )

            spantree_after = (
                capture_snapshot()
            )

            print_summary()

            disable_debug()

            log(
                "[%s] Script finished."
                % timestamp()
            )

            break

        time.sleep(
            POLL_INTERVAL
        )


if __name__ == "__main__":
    main()
