# 1. Compound a high-viscosity orthopedic Bone Marrow Concentrate (BMC) batch
python huesOS_marrow_variants.py compound-marrow --batch-id "BMC-JOINT-01" --variant bmc --volume 2.0 --fda-id "IND-TOKEN-881A"

# 2. Compound a high-oxygenation Hematopoietic Stem Cell (HSC) batch for oncological use
python huesOS_marrow_variants.py compound-marrow --batch-id "HSC-ONCO-44" --variant hsc --volume 1.0 --fda-id "IND-TOKEN-112B"

# 3. Test the automated safety lockout by omitting the required patient waiver
python huesOS_marrow_variants.py compound-marrow --batch-id "FAIL-TEST" --variant msc --volume 1.0
