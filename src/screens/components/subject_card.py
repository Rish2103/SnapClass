import streamlit as st


def subject_card(name, code, section, stats=None, footer_callback=None, pct_badge=None):
    badge_html = ""
    if pct_badge:
        pct_val, is_safe = pct_badge
        if is_safe:
            badge_html = f'<span style="float:right; background:#E8F8F5; color:#117A65; border:1px solid #2ECC71; padding:4px 12px; border-radius:15px; font-weight:700; font-size:0.9rem;">📈 {pct_val:.0f}% (Safe)</span>'
        else:
            badge_html = f'<span style="float:right; background:#FFEAEF; color:#C0113B; border:1px solid #FF4D6D; padding:4px 12px; border-radius:15px; font-weight:700; font-size:0.9rem;">⚠️ {pct_val:.0f}% (Low Attendance Alert)</span>'

    html = f"""
        <div style="background:white; border-left: 8px solid #EB459E; padding:25px; border-radius: 20px; border: 1px solid black; margin-bottom:20px;">
        {badge_html}
        <h3 style="margin:0; color: #1e293b; font-size: 1.5rem ">{name}</h3>
        <p style="color:#64748b; margin:10px 0;">Code : <span style="background:#E0E3FF; color:#5865F2; padding:2px 8px; border-radius:5px;">{code} </span> | Section : {section}</p>
        
        """

    if stats:
        html += """
        <div style="display:flex; gap:8px; flex-wrap:wrap;">
        """
        for icon, label, value in stats:
            html += f'<div style="background: #EB459E10; padding:5px 12px; border-radius:12px; font-size:0.9rem">{icon} <b>{value}</b> {label} </div>'

        html += "</div>"

    st.markdown(html, unsafe_allow_html=True)

    if footer_callback:
        footer_callback()

