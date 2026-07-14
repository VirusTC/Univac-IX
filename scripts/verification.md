### **Verification and Execution Suite**

Your development team can execute separate commands to run or audit either manufacturing loop independently:

```bash
# 1. Run an isolated batch of Recombinant Plant/Apiary Plasma
python biomed_component_manufacturing.py manufacture-plasma --batch-id "PLASMA-ONLY-04" --volume 5.0 --fda-id "MIL-IRB-CCCRP-99B"

# 2. Run an isolated batch of VerduraRX Hemoglobin Oxygen Carriers
python biomed_component_manufacturing.py manufacture-hemoglobin --batch-id "HEMO-ONLY-12" --volume 2.5 --peroxide 0.01 --po2 95.0 --fda-id "IND-FORM-3926-C"

# 3. Test the peroxide toxicity threshold safety shutdown on the hemoglobin line
python biomed_component_manufacturing.py manufacture-hemoglobin --batch-id "HEMO-TOXIC-TEST" --volume 1.0 --peroxide 0.08 --fda-id "IND-FORM-3926-C"
