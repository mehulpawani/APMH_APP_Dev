import streamlit as st

def calculate_total_income(regime, salary, business_income, house_income, other_sources):
    # Salary – Apply standard deduction
    if regime == 'new':
        salary -= 75000
    else:
        salary -= 50000

    # House Property – Apply 30% standard deduction
    house_income *= 0.70

    # Total income excluding capital gains
    total = max(0, salary) + max(0, business_income) + max(0, house_income) + max(0, other_sources)
    return total


def calculate_tax_old_regime(total_income, stcg, ltcg):
    tax = 0

    # Slab-based tax
    if total_income <= 250000:
        tax = 0
    elif total_income <= 500000:
        tax = (total_income - 250000) * 0.05
    elif total_income <= 1000000:
        tax = 12500 + (total_income - 500000) * 0.2
    else:
        tax = 112500 + (total_income - 1000000) * 0.3

    # Capital gains
    tax += stcg * 0.20
    if ltcg > 125000:
        tax += (ltcg - 125000) * 0.125

    # Rebate under 87A
    if total_income <= 500000:
        tax -= min(12500, tax)

    tax = max(tax, 0)
    return round(tax * 1.04, 2)


def calculate_tax_new_regime(total_income, stcg, ltcg):
    tax = 0
    slabs = [
        (400000, 0.00),
        (400000, 0.05),
        (400000, 0.10),
        (400000, 0.15),
        (400000, 0.20),
        (400000, 0.25),
        (float('inf'), 0.30)
    ]

    limit = 0
    for slab, rate in slabs:
        if total_income > limit + slab:
            tax += slab * rate
            limit += slab
        else:
            tax += (total_income - limit) * rate
            break

    # Capital gains
    tax += stcg * 0.20
    if ltcg > 125000:
        tax += (ltcg - 125000) * 0.125

    # Rebate under 87A (new regime)
    if total_income <= 1200000:
        tax -= min(60000, tax)

    tax = max(tax, 0)
    return round(tax * 1.04, 2)


# ==== STREAMLIT APP ====
st.title("💰 Income Tax Calculator (India)")

st.sidebar.header("Input Your Details")

regime = st.sidebar.radio("Choose Regime", ("old", "new"))

salary = st.sidebar.number_input("Salary Income (₹)", min_value=0.0, step=1000.0)
business_income = st.sidebar.number_input("Business/Professional Income (₹)", min_value=0.0, step=1000.0)
house_income = st.sidebar.number_input("Net Annual Value from House Property (₹)", min_value=0.0, step=1000.0)
other_sources = st.sidebar.number_input("Income from Other Sources (₹)", min_value=0.0, step=1000.0)
stcg = st.sidebar.number_input("Short-Term Capital Gains (₹)", min_value=0.0, step=1000.0)
ltcg = st.sidebar.number_input("Long-Term Capital Gains (₹)", min_value=0.0, step=1000.0)
tds_paid = st.sidebar.number_input("TDS/Advance Tax Paid (₹)", min_value=0.0, step=1000.0)

if st.sidebar.button("Calculate Tax"):
    total_income = calculate_total_income(regime, salary, business_income, house_income, other_sources)

    if regime == 'old':
        total_tax = calculate_tax_old_regime(total_income, stcg, ltcg)
    else:
        total_tax = calculate_tax_new_regime(total_income, stcg, ltcg)

    net_tax = total_tax - tds_paid
    status = "Refund Due 💵" if net_tax < 0 else "Tax Payable 🧾"

    # ==== OUTPUT ====
    st.subheader("📊 Tax Summary")
    st.write(f"**Total Taxable Income (Excl. CG):** ₹{total_income:,.2f}")
    st.write(f"**Total Tax Liability (incl. cess):** ₹{total_tax:,.2f}")
    st.write(f"**TDS/Advance Tax Paid:** ₹{tds_paid:,.2f}")
    st.success(f"**{status}: ₹{abs(net_tax):,.2f}**")
