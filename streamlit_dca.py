import streamlit as st
import pandas as pd
import altair as alt
import numpy as np

from resaid.dca import decline_solver, decline_curve

from scipy.optimize import root


def dca_calc(qi=None, qf=None, de=None, dmin=None, b=None, eur=None, t_max=None):

    l_dca = decline_curve()
    l_dca.D_MIN = dmin

    l_solver = decline_solver(
        qi=qi,
        qf=qf,
        de=de,
        dmin=dmin,
        b=b,
        eur=eur,
        t_max=t_max
    )

    qi, t_max, qf, de, eur, warning_flag, delta = l_solver.solve()

    t_range = np.array(range(0,int(t_max)))
    l_tc = l_dca.arps_decline(t_range,qi=qi,di=de,b=b,t0=0)

    
    r_df = pd.DataFrame({
        't':t_range,
        'q':l_tc
    })

    r_df = r_df[r_df['q']>0]

    return r_df, qi, qf, de, eur, t_max, warning_flag, delta

def make_graph(input_df):

    nearest = alt.selection_point(nearest=True, on='mouseover',
                        fields=['t'], empty=False)
    

    base = alt.Chart(input_df).mark_line().encode(
        x=alt.X('t:Q', axis=alt.Axis(title='Time Step, months')),
        y=alt.Y('q:Q', axis=alt.Axis(title='Rate')).scale(type='log'),
    )



    selectors = base.mark_point().encode(
        opacity=alt.value(0),
        tooltip='t:Q'
    ).add_params(
        nearest
    )
   

    # Draw text labels near the points, and highlight based on selection
    text = base.mark_text(align='left', dx=5, dy=-5).encode(
        text=alt.condition(nearest, 'q:Q', alt.value(' '))
    )



    rules = base.mark_rule(color='gray').encode(
        x='t:Q',
        #tooltip='month:T'
    ).transform_filter(
        nearest
    )

    # Combine the charts
    final_chart = alt.layer(
        base, text, selectors,rules,  #gas_text
    ).properties(
        width=600, height=300
    )


    

    return final_chart

if __name__ == '__main__':

    col1, col2 = st.columns([.3,.7])

    with col1:
        st.header("Inputs")
        qi_input = st.checkbox('Input qi', value=True)
        qf_input = st.checkbox('Input qf')
        de_input = st.checkbox('Input decline', value=True)
        eur_input = st.checkbox('Input EUR')
        t_input = st.checkbox('Input number of months', value=True)
        de_method = st.radio(
            label="Decline input method",
            options=["Nominal", "Effective"],
            index=0
        )

    true_list = [
        qi_input,
        qf_input,
        de_input,
        eur_input,
        t_input
    ]

    

    with col1:
        qi = st.number_input('Inital rate, volume/month', min_value=0, value=100, step=10, disabled=not qi_input)
        qf = st.number_input('Final rate, volume/month', min_value=0, value=100, max_value=qi, step=10, disabled=not qf_input)
        ai = st.number_input('Initial decline (Nominal), %/Year', min_value=6, value=50, step=1,disabled=((not de_input) | (de_method!="Nominal")))
        de = st.number_input('Initial decline (Effective), %/Year', min_value=6, value=50, max_value=100, step=1,disabled=((not de_input) | (de_method!="Effective")))
        b = st.slider('B Factor', min_value=0.01, max_value=2.0, value=.5, step=.01)
        dmin = st.number_input('Minimum decline, %/Year',min_value=1, max_value=de, value=6,step=1)
        t_max = st.slider('Number of months', min_value=1, max_value=600, value=300, step=1, disabled=not t_input)
        eur = st.number_input('EUR, volume',min_value=1, value=50000,step=100, disabled=not eur_input)

    if true_list.count(True)==3:

        if not qi_input:
            qi = None
        
        if not qf_input:
            qf = None

        if not de_input:
            ai = None
        else:
            if de_method == 'Nominal':
                ai = ai/(100*12)
            else:
                ai = 1/b*((1-de/100)**(-b)-1)
                ai = ai/12

        if not eur_input:
            eur = None

        if not t_input:
            t_max = None

    

        l_df, qi, qf, de, eur, t_max, warning_flag, delta = dca_calc(qi=qi, qf=qf, de=ai, dmin=dmin/(100*12), b=b, eur=eur, t_max=t_max)

        eur_check = l_df['q'].sum()

        ai = de*12
        de = (1-np.power((ai*b+1),(-1/b)))

        altair_chart = make_graph(l_df)

        with col2:
            st.header("Graph")
            st.altair_chart(altair_chart, use_container_width=False, theme="streamlit")

        with col2:
            if warning_flag != 0:
                st.warning('Result did not converge, check EUR delta.', icon="⚠️")
            st.header("Results")
            st.metric(label="qi", value=f"{round(qi,0):,.0f}", delta=None)
            st.metric(label="qf", value=f"{round(qf,0):,.0f}", delta=None)
            st.metric(label="Norminal Decline", value=f"{int(round(ai*100,0))} %/Yr", delta=None)
            st.metric(label="Effective Decline", value=f"{int(round(de*100,0))} %/Yr", delta=None)
            st.metric(label="EUR", value=f"{eur_check:,.0f}", delta=f"{delta:,.0f}")
            st.metric(label="Months", value=f"{t_max:,.0f}", delta=None)
    



