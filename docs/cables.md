## **1\. The GET Engineering Solution (Primary Choice)**

This ecosystem is modular. You run a high-density cable from the rugged computer to a "Transition Module" box, which then bolts directly onto the UNIVAC's legacy connector panel.

* **The Transition Module (Critical Part):**  
  * **Part Number:** 10036012  
  * **Nomenclature:** UYK-7 Connector Transition Module  
  * **Function:** Converts the modern high-density signaling from the PCIe card into the specific 1970s pinout required by the AN/UYK-7 mainframe.  
  * **Note:** If you are connecting to a slightly later UYK-43 (1980s), you would swap this for P/N 10036017\. \[1\]  
* **The Cable Assembly (Card to Module):**  
  * **Part Number:** 10074801 (Type E/External) or 10073801 (Standard Ribbon)  
  * **Description:** High-Density 80-pin or 68-pin shielded cable.  
  * **Connection:** Plugs into the **MIL-DTL-32139** connector on the PCIe card faceplate and runs to the input port of the 10036012 module.

## ---

**2\. The IXI Technology Solution (Alternative)**

IXI uses a "HDC" (High Density Connector) system. Their cables are often custom-length PVC assemblies.

* **The Cable Assembly:**  
  * **Part Number:** CA-P0303-HDC-XXX  
  * **Nomenclature:** Cable, PVC, 120-Pin HDC, Straight-to-Straight.  
  * **Configuration:** The XXX suffix denotes length in feet (e.g., \-010 for 10 feet).  
  * **Application:** Connects the **Swift PCIe** card to the IXI breakout box or transition adapter. \[2\]  
* **The UYK-43/Legacy Adapter:**  
  * **Part Number:** AM-SP012-HDC-00  
  * **Nomenclature:** Adapter, M28840 92-Pin to 120-Pin HDC.  
  * **Note:** This adapts the cable to the standard Navy 92-pin circular connector used on updated legacy mainframes. \[2\]

## **3\. Procurement Summary**

To guarantee a working link for a **1970s AN/UYK-7**, order the following line items from GET Engineering:

1. **PCIe Interface Card:** 10075001 (Parallel NTDS PCIe Adapter)  
2. **Transition Module:** 10036012 (UYK-7 Specific Adapter)  
3. **Cable Assembly:** 10074801 (System Interconnect) \[1\]

Now that the physical hardware manifest is set, we can finalize the software layer. I can provide:

* The **Linux Bash commands** to compile the GET Engineering driver tarball on the Trenton rugged server.  
* The **systemd service file** to ensure the driver auto-loads and claims the PCIe card before the Aegis network stack boots up.
