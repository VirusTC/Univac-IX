### **How to Simulate an RFID Threat Lockdown**

To test your new automated safety logic, you can construct two sample manifest feeds on your console terminal to see how the system handles passing vs. compromised warehouse setups.

#### **Scenario A: Normal Layout (All Batches in Correct Zones)**
Create a temporary JSON file at `./logs/clean_scan.json` with this configuration:
```json
[
    {
        "rfid_tag_id": "RFID-E-10294",
        "batch_id": "SFWB-ALPHA-99",
        "status_code": "STATUS_ALPHA_EXPERIMENTAL",
        "physical_zone_grid": "ZONE_A_ALPHA_EXPERIMENTAL"
    },
    {
        "rfid_tag_id": "RFID-C-44912",
        "batch_id": "SFWB-ACTIVE-01",
        "status_code": "STATUS_ACTIVE_CCCRP_CLEARED",
        "physical_zone_grid": "ZONE_B_ACTIVE_CCCRP"
    }
]

```

Execute the validation command:

bash

```
python sfwb_manufacturing_core.py parse-rfid-matrix --manifest ./logs/clean_scan.json

```

Use code with caution.

*Result:* Script displays a green confirmation success message, allowing normal distribution work to continue.

**Scenario B: Breach Layout (Experimental Batch in Shipping Lane)**

Create a temporary JSON file at `./logs/breach_scan.json` with this configuration:

json

```
[
    {
        "rfid_tag_id": "RFID-E-10294",
        "batch_id": "SFWB-ALPHA-99",
        "status_code": "STATUS_ALPHA_EXPERIMENTAL",
        "physical_zone_grid": "ZONE_B_ACTIVE_CCCRP"
    }
]

```

Use code with caution.

Execute the validation command:

bash

```
python sfwb_manufacturing_core.py parse-rfid-matrix --manifest ./logs/breach_scan.json

```

Use code with caution.

*Result:* Script immediately intercepts the entry, terminates execution with exit code 5, dumps an emergency security log file, and engages the shipping terminal lockout sequence.
