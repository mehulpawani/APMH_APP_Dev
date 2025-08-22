import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# TAX CALCULATION FUNCTIONS (Final Corrected Version with Marginal Relief)

def calculate_total_income(regime, salary, business_income, house_income, other_sources, house_loan_interest=0):
    # Salary – Apply standard deduction
    if regime == 'new':
        salary -= 75000
    else:
        salary -= 50000
    # House Property – Apply 30% standard deduction THEN subtract loan interest
    house_income *= 0.70
    house_income -= house_loan_interest  # Deduct interest on house property loan
    # Total income excluding capital gains
    total = max(0, salary) + max(0, business_income) + max(0, house_income) + max(0, other_sources)
    return total

def calculate_surcharge_rate(total_income, regime, capital_gains_income):
    """Determine surcharge rate based on total income & regime, with CG max 15%"""
    rate = 0
    if total_income > 50000000:  # > 5 cr
        rate = 0.37 if regime == "old" else 0.25
    elif total_income > 20000000:  # 2–5 cr
        rate = 0.25
    elif total_income > 10000000:  # 1–2 cr
        rate = 0.15
    elif total_income > 5000000:   # 50L–1cr
        rate = 0.10
    # Capital gains surcharge cap at 15%
    if capital_gains_income > 0 and rate > 0.15:
        rate = 0.15
    return rate

def calculate_tax_old_regime(total_income, stcg, ltcg):
    # Base tax (normal income)
    tax = 0
    if total_income <= 250000:
        tax = 0
    elif total_income <= 500000:
        tax = (total_income - 250000) * 0.05
    elif total_income <= 1000000:
        tax = 12500 + (total_income - 500000) * 0.2
    else:
        tax = 112500 + (total_income - 1000000) * 0.3
    
    # Capital gains tax (separate calculation)
    cg_tax = stcg * 0.20
    if ltcg > 125000:
        cg_tax += (ltcg - 125000) * 0.125
    
    # Apply rebate ONLY to regular income tax (NOT capital gains)
    rebate_applied = 0
    if total_income <= 500000:  # ₹5L limit
        rebate_applied = min(12500, tax)  # Max ₹12.5K rebate on regular tax only
        tax_after_rebate = max(0, tax - rebate_applied)
    else:
        tax_after_rebate = tax
    
    # Total tax = Regular tax (after rebate) + Capital gains tax (no rebate)
    total_tax_before_surcharge = tax_after_rebate + cg_tax
    
    # Surcharge
    surcharge_rate = calculate_surcharge_rate(total_income + stcg + ltcg, "old", stcg + ltcg)
    surcharge = total_tax_before_surcharge * surcharge_rate
    
    # Cess
    cess = (total_tax_before_surcharge + surcharge) * 0.04
    
    return round(max(total_tax_before_surcharge, 0), 2), round(surcharge, 2), round(cess, 2), round(rebate_applied, 2), 0

def calculate_tax_new_regime(total_income, stcg, ltcg):
    # NEW REGIME TAX SLABS FOR FY 2024-25
    slabs = [
        (400000, 0.00),    # 0 to 4L: 0%
        (400000, 0.05),    # 4L to 8L: 5%
        (400000, 0.10),    # 8L to 12L: 10%
        (400000, 0.15),    # 12L to 16L: 15%
        (400000, 0.20),    # 16L to 20L: 20%
        (400000, 0.25),    # 20L to 24L: 25%
        (float('inf'), 0.30)  # Above 24L: 30%
    ]
    
    # Step 1: Apply LTCG exemption of ₹1.25L first
    exempt_ltcg = min(ltcg, 125000)
    taxable_ltcg_after_exemption = max(0, ltcg - exempt_ltcg)
    
    # Step 2: Calculate available basic exemption (₹4,00,000 for new regime)
    basic_exemption_limit = 400000
    
    # Step 3: Apply basic exemption in priority order
    # Priority: 1. Other income, 2. STCG, 3. Taxable LTCG
    remaining_exemption = basic_exemption_limit
    
    # Use exemption for other income first
    other_income_exempted = min(total_income, remaining_exemption)
    remaining_exemption = max(0, remaining_exemption - other_income_exempted)
    taxable_other_income = max(0, total_income - other_income_exempted)
    
    # Use remaining exemption for STCG
    stcg_exempted = min(stcg, remaining_exemption)
    remaining_exemption = max(0, remaining_exemption - stcg_exempted)
    taxable_stcg = max(0, stcg - stcg_exempted)
    
    # Use remaining exemption for taxable LTCG
    ltcg_exempted = min(taxable_ltcg_after_exemption, remaining_exemption)
    final_taxable_ltcg = max(0, taxable_ltcg_after_exemption - ltcg_exempted)
    
    # Step 4: Calculate tax on REGULAR income starting from appropriate slab
    regular_tax = 0
    
    if taxable_other_income > 0:
        exemption_used_from_regular = other_income_exempted
        
        if exemption_used_from_regular >= 400000:
            # Full ₹4L exemption used from regular income
            # Start from ₹4L-8L slab (index 1)
            income_remaining = taxable_other_income
            
            # Apply slabs starting from 4L-8L (5%)
            for i in range(1, len(slabs)):  # Start from index 1 (₹4L-8L slab)
                slab_limit, rate = slabs[i]
                
                if income_remaining <= 0:
                    break
                
                taxable_in_slab = min(income_remaining, slab_limit)
                regular_tax += taxable_in_slab * rate
                income_remaining -= taxable_in_slab
        else:
            # Partial exemption used from regular income
            remaining_in_first_slab = 400000 - exemption_used_from_regular
            income_remaining = taxable_other_income
            
            # If there's still room in the 0% slab
            if remaining_in_first_slab > 0:
                tax_free_amount = min(income_remaining, remaining_in_first_slab)
                income_remaining -= tax_free_amount
            
            # Apply remaining slabs
            for i in range(1, len(slabs)):
                if income_remaining <= 0:
                    break
                
                slab_limit, rate = slabs[i]
                taxable_in_slab = min(income_remaining, slab_limit)
                regular_tax += taxable_in_slab * rate
                income_remaining -= taxable_in_slab
    
    # Step 5: Calculate capital gains tax separately
    cg_tax = taxable_stcg * 0.20 + final_taxable_ltcg * 0.125
    
    # Step 6: Apply rebate ONLY to regular income tax (NOT capital gains)
    rebate_applied = 0
    if total_income <= 1200000:  # ₹12L limit
        rebate_applied = min(60000, regular_tax)  # Max ₹60K rebate on regular tax only
        regular_tax_after_rebate = max(0, regular_tax - rebate_applied)
    else:
        regular_tax_after_rebate = regular_tax
    
    # Step 7: Total tax = Regular tax (after rebate) + Capital gains tax (no rebate)
    total_tax_before_surcharge = regular_tax_after_rebate + cg_tax
    
    # Step 8: Apply Marginal Relief for income between ₹12L to ₹12.6L
    marginal_relief_applied = 0
    total_taxable_income = total_income + stcg + ltcg
    
    if 1200000 < total_taxable_income <= 1260000:
        # Calculate tax without rebate for marginal relief comparison
        tax_without_rebate = regular_tax + cg_tax
        
        # Marginal relief calculation
        marginal_relief_amount = total_taxable_income - 1200000
        
        # Apply marginal relief - tax cannot exceed the excess over ₹12L
        if total_tax_before_surcharge > marginal_relief_amount:
            marginal_relief_applied = total_tax_before_surcharge - marginal_relief_amount
            total_tax_before_surcharge = marginal_relief_amount
    
    # Step 9: Calculate surcharge
    surcharge_rate = calculate_surcharge_rate(total_income + stcg + ltcg, "new", stcg + ltcg)
    surcharge = total_tax_before_surcharge * surcharge_rate
    
    # Step 10: Calculate cess
    cess = (total_tax_before_surcharge + surcharge) * 0.04
    
    return round(max(total_tax_before_surcharge, 0), 2), round(surcharge, 2), round(cess, 2), round(rebate_applied, 2), round(marginal_relief_applied, 2)

# STREAMLIT UI START - ENHANCED VERSION

st.set_page_config(
    page_title="APMH Tax Calculator", 
    page_icon="💰", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Advanced CSS styling with beige theme
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stApp {
        background-color: #F5F5DC;
        color: #5A4E3A;
    }
    .main-header {
        background-color: #D2B48C;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        color: #5A4E3A;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .input-container {
        background: #FFF8DC;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        margin-bottom: 2rem;
    }
    .result-container {
        background: #F5F5DC;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        color: #5A4E3A;
    }
    .metric-card {
        background: #FFF8DC;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        margin: 0.5rem;
        text-align: center;
        color: #5A4E3A;
    }
    .stButton > button {
        background-color: #D2B48C;
        color: #5A4E3A;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 25px;
        font-weight: bold;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #C19A6B;
        box-shadow: 0 6px 12px rgba(0,0,0,0.3);
        transform: translateY(-2px);
    }
    .sidebar .sidebar-content {
        background-color: #F5F5DC;
        color: #5A4E3A;
    }
    a {
        color: #996515;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
    <div class="main-header">
        <h1>💼 APMH Income Tax Calculator</h1>
        <p>Income Tax Planning & Calculation Tool | AY 2026-27 </p>
    </div>
""", unsafe_allow_html=True)

# Sidebar for regime comparison
with st.sidebar:
    st.markdown("### 📊 Quick Regime Comparison")
    st.info("""
    **Old Regime Features:**
    - Standard deduction (₹50,000)
    - Multiple deductions available
    - Basic exemption: ₹2.5L
    - **Rebate: Up to ₹5L income, max ₹12.5K**
    
    **New Regime Features:**
    - Higher standard deduction (₹75,000)
    - Limited deductions
    - Basic exemption: ₹4L
    - **Rebate: Up to ₹12L income, max ₹60K**
    - **🆕 Marginal Relief: ₹12L-₹12.6L income**
    - **Smart CG exemption utilization**
    """)
    
    st.markdown("### 📈 Tax Slabs")
    regime_info = st.selectbox("View details for:", ["New Regime", "Old Regime"])
    
    if regime_info == "New Regime":
        st.markdown("""
        - **₹0 - 4L:** 0%
        - **₹4L - 8L:** 5%
        - **₹8L - 12L:** 10%
        - **₹12L - 16L:** 15%
        - **₹16L - 20L:** 20%
        - **₹20L - 24L:** 25%
        - **Above ₹24L:** 30%
        
        **🆕 Special Benefits:**
        - **Rebate:** ₹60K for income ≤ ₹12L
        - **Marginal Relief:** Income ₹12L-₹12.6L
        - Tax limited to (Income - ₹12L)
        
        **CG Exemption Priority:**
        1. Other income uses ₹4L exemption
        2. STCG uses remaining exemption
        3. LTCG (after ₹1.25L) uses last
        
        **Tax Rates:** STCG: 20% | LTCG: 12.5%
        """)
    else:
        st.markdown("""
        **Old Regime:**
        - **₹0 - 2.5L:** 0%
        - **₹2.5L - 5L:** 5%
        - **₹5L - 10L:** 20%
        - **Above ₹10L:** 30%
        
        **Capital Gains:**
        - **STCG:** 20%
        - **LTCG:** 12.5% (above ₹1.25L)
        """)

# The rest of the code remains unchanged...
# (Include all remaining code for tabs, forms, calculations, and footer as in the original)

