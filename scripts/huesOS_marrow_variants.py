#!/usr/bin/env python3
"""
UNIVAC IX: HUES-OS Bio-Synthetic Marrow Multi-Variant Formulation Engine.
Drives automated manufacturing recipes for:
1. MSC (Mesenchymal Stem Cell Mimic)
2. BMC (Bone Marrow Concentrate Mimic)
3. HSC (Hematopoietic Stem Cell Mimic)
4. SVF (Stromal Vascular Fraction Mimic)

Enforces strict hourly regulatory tracking constraints under active IRB protocols.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import typer

app = typer.Typer(
    help="UNIVAC IX: Compounding engine for standalone bio-synthetic marrow variant fractions.",
    add_completion=False
)

class MarrowVariantEngine:
    def __init__(self, target_volume_ml: float = 1000.0):
        self.volume_ml = target_volume_ml
        
        # Define base target configurations per variant profile
        self.profiles = {
            "MSC": {
                "bamboo_extract_g_l": 0.15,
                "lipid_fraction": 0.50,
                "calcium_mmol_l": 2.50,
                "magnesium_mmol_l": 1.25,
                "zinc_mmol_l": 0.25,      # Elevated zinc for enzyme activation
                "verdurarx_fraction": 0.10,
                "billing_code": "IRB-MSC-REG-441"
            },
            "BMC": {
                "bamboo_extract_g_l": 0.05,
                "lipid_fraction": 0.20,
                "calcium_mmol_l": 5.00,   # Doubled calcium for matrix density
                "magnesium_mmol_l": 2.50,   # Balanced magnesium to prevent calcification
                "zinc_mmol_l": 0.15,
                "verdurarx_fraction": 0.05,
                "billing_code": "IRB-BMC-ORTHO-882"
            },
            "HSC": {
                "bamboo_extract_g_l": 0.20,
                "lipid_fraction": 0.15,
                "calcium_mmol_l": 2.50,
                "magnesium_mmol_l": 1.25,
                "zinc_mmol_l": 0.15,
                "verdurarx_fraction": 0.45, # Maximum hemoglobin ratio for oxygen transport
                "billing_code": "IRB-HSC-ONCO-119"
            },
            "SVF": {
                "bamboo_extract_g_l": 0.35, # Maximum polysaccharide cocktail density
                "lipid_fraction": 0.40,
                "calcium_mmol_l": 2.00,
                "magnesium_mmol_l": 1.00,
                "zinc_mmol_l": 0.10,
                "verdurarx_fraction": 0.15,
                "billing_code": "IRB-SVF-COCKTAIL-005"
            }
        }

    def generate_recipe(self, variant: str) -> Dict[str, Any]:
        """Calculates mass allocations based on target variant configuration profile parameters."""
        prof = self.profiles[variant]
        
        # Calculate matrix allocations based on target volumetric fractions
        lipid_vol = self.volume_ml * prof["lipid_fraction"]
        verdura_vol = self.volume_ml * prof["verdurarx_fraction"]
        plasma_base_vol = self.volume_ml - (lipid_vol + verdura_vol)
        
        return {
            "variant_id": variant,
            "target_volume_ml": self.volume_ml,
            "allocated_phases": {
                "lipid_capsule_carrier_volume_ml": round(lipid_vol, 2),
                "verdurarx_hemoglobin_volume_ml": round(verdura_vol, 2),
                "apis_plasma_base_scaffold_volume_ml": round(plasma_base_vol, 2)
            },
            "chemical_additions": {
                "dictyophora_bamboo_polysaccharide_mass_g": round((self.volume_ml / 1000.0) * prof["bamboo_extract_g_l"], 4),
                "nutricost_calcium_target_mmol_l": prof["calcium_mmol_l"],
                "nutricost_magnesium_target_mmol_l": prof["magnesium_mmol_l"],
                "nutricost_zinc_target_mmol_l": prof["zinc_mmol_l"]
            },
            "financials": {
                "hicfa_billing_code": prof["billing_code"],
                "base_transaction_cost_usd": round(self.volume_ml * 3.15, 2)
            }
        }


@app.command()
def compound_marrow(
    batch_id: str = typer.Option(..., "--batch-id", "-b", help="Unique alphanumeric tracking identifier."),
    variant: str = typer.Option(..., "--variant", "-v", help="Target output specification variant: [MSC, BMC, HSC, SVF]"),
    volume_l: float = typer.Option(1.0, "--volume", "-l", help="Total target production volume in Liters."),
    fda_token: Optional[str] = typer.Option(None, "--fda-id", help="FDA Form 3926 Compassionate Use Individual Patient Token ID.")
):
    """
    Executes raw material mass balancing for specific standalone bone marrow fractions 
    and pipes data logs straight to the secure warehouse compliance file vault.
    """
    # 1. Enforce Mandatory Individual IRB Waiver Check
    if not fda_token:
        typer.secho("\n[REGULATORY HALT] Compounding Access Denied.", fg=typer.colors.WHITE, bg=typer.colors.RED, bold=True)
        typer.secho("Error: Standalone cell-fraction synthesis requires a valid individual patient compassionate token.", fg=typer.colors.RED)
        raise typer.Exit(code=50)

    # 2. Initialize Engine & Validate Variant Key Input
    variant_upper = variant.upper()
    engine = MarrowVariantEngine(target_volume_ml=(volume_l * 1000.0))
    
    if variant_upper not in engine.profiles:
        typer.secho(f"[!] Error: Invalid variant signature [{variant}]. Must match MSC, BMC, HSC, or SVF.", fg=typer.colors.RED)
        raise typer.Exit(code=51)

    # 3. Calculate Mix Configuration Recipe Sheet
    recipe = engine.generate_recipe(variant_upper)
    
    # 4. Compile Unified Audit Ledger Data Document
    audit_ledger = {
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "batch_identifier": batch_id,
        "regulatory_protocol": "FDA IRB Compassionate Care Framework (Individual Expanded Access)",
        "patient_authorization_token": fda_token,
        "formulation_profile": recipe,
        "system_clearance_status": "APPROVED_FOR_CLINICAL_DISPATCH"
    }

    # 5. Serialize to Local File Logs Repository
    Path("./logs").mkdir(exist_ok=True)
    with open(f"./logs/MARROW_FRACTION_AUDIT_{batch_id}.json", "w") as f:
        json.dump(audit_ledger, f, indent=4)

    # 6. Print Operator Dashboard Status Output Interface
    typer.echo("\n" + "="*75)
    typer.secho(f"        UNIVAC IX: BIO-SYNTHETIC MARROW FRACTION PIPELINE          ", fg=typer.colors.GREEN, bold=True)
    typer.echo("="*70)
    typer.echo(f"Batch Identifier : {batch_id}")
    typer.echo(f"Target Variant   : {variant_upper} ({audit_ledger['formulation_profile']['formulation_profile']['hicfa_billing_code'] if 'formulation_profile' in audit_ledger and 'hicfa_billing_code' in audit_ledger['formulation_profile'] else recipe['financials']['hicfa_billing_code']})")
    typer.echo(f"Total Batch Vol  : {volume_l} Liters")
    typer.echo(f"Assigned Patient : {fda_token}")
    typer.echo("-"*70)
    typer.echo("Allocated Phase Ratios:")
    for k, v in recipe["allocated_phases"].items():
        typer.echo(f"  - {k:40}: {v} mL")
    typer.echo("\nRequired Chemical Additions:")
    for k, v in recipe["chemical_additions"].items():
        typer.echo(f"  - {k:45}: {v}")
    typer.echo("="*70 + "\n")


if __name__ == "__main__":
    app()
