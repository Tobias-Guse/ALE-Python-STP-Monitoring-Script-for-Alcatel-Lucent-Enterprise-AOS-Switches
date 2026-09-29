Python STP Monitoring Script for Alcatel-Lucent Enterprise AOS Switches

Overview
The STP Monitoring Script is designed to simplify the troubleshooting of Spanning Tree Protocol (STP) issues on Alcatel-Lucent Enterprise (AOS) switches.
The script automatically enables STP debug logging, monitors STP-related events in real time, captures STP topology information before and after monitoring, and generates a detailed summary report to help identify Layer 2 instability, Root Bridge changes, and potential network loops.

Features
Enables STP debug logging automatically
Monitors STP activity for a configurable time period
Captures STP snapshots before and after monitoring
Detects Root Bridge changes
Detects Count-To-Infinity (CTI) events
Detects Priority Mismatch events
Detects RSTP CTI activation events
Tracks Root Priority transitions
Collects VLAN statistics
Collects Root Priority and Root MAC information
Tracks STP-related port activity
Records Root Change timelines
Compares STP topology before and after monitoring
Calculates Topology Change deltas per VLAN
Identifies Root and Non-Root VLAN instances
Automatically restores STP logging to the default level when the monitoring period ends

Example Summary Output
============================================================
STP MONITORING SUMMARY
============================================================

Runtime : 10 min

------------------------------------------------------------
STP ANOMALIES
------------------------------------------------------------

Root Changes             : 2
Count To Infinity Events : 35
Priority Mismatch Events : 35
RSTP CTI Events          : 35

------------------------------------------------------------
VLAN 100
------------------------------------------------------------

Role               : ROOT BRIDGE
Priority           : 4096
Root Port          : None

Topology Changes   : 1 -> 7 (Delta = 6)

Last TC Port       : 1/1/10
Last TC Bridge     : 2000-94:24:e1:60:83:99

------------------------------------------------------------
VLAN 200
------------------------------------------------------------

Role               : NON ROOT BRIDGE
Priority           : 32768
Root Port          : 1/1/10

Topology Changes   : 3 -> 18 (Delta = 15)

Last TC Port       : 1/1/10
Last TC Bridge     : 1000-94:24:e1:60:83:99

------------------------------------------------------------
POTENTIAL ROOT CAUSE
------------------------------------------------------------

Most Active Port : 1/1/10

Observed Symptoms

- Root Bridge Change
- Count To Infinity
- Priority Mismatch
- RSTP CTI Activation
