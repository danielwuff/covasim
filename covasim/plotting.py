'''
Core plotting functions for simulations, multisims, and scenarios.

Also includes Plotly-based plotting functions to supplement the Matplotlib based
ones that are of the Sim and Scenarios objects. Intended mostly for use with the
webapp.
'''

import numpy as np
import pylab as pl
import sciris as sc
import datetime as dt
import matplotlib.ticker as ticker
import plotly.graph_objects as go
from . import defaults as cvd


__all__ = ['plot_sim', 'plot_scens', 'plot_result', 'plot_compare', 'plot_transtree', 'animate_transtree', 'plotly_sim', 'plotly_people', 'plotly_animate']


#%% Plotting helper functions

def handle_args(fig_args=None, plot_args=None, scatter_args=None, axis_args=None, fill_args=None, legend_args=None):
    ''' Handle input arguments -- merge user input with defaults '''
    args = sc.objdict()
    args.fig     = sc.mergedicts({'figsize': (16, 14)}, fig_args)
    args.plot    = sc.mergedicts({'lw': 3, 'alpha': 0.7}, plot_args)
    args.scatter = sc.mergedicts({'s':70, 'marker':'s'}, scatter_args)
    args.axis    = sc.mergedicts({'left': 0.10, 'bottom': 0.05, 'right': 0.95, 'top': 0.97, 'wspace': 0.25, 'hspace': 0.25}, axis_args)
    args.fill    = sc.mergedicts({'alpha': 0.2}, fill_args)
    args.legend  = sc.mergedicts({'loc': 'best'}, legend_args)
    return args


def handle_to_plot(which, to_plot, n_cols):
    ''' Handle which quantities to plot '''

    if to_plot is None:
        if which == 'sim':
            to_plot = cvd.get_sim_plots()
        elif which =='scens':
            to_plot = cvd.get_scen_plots()
        else:
            errormsg = f'"which" must be "sim" or "scens", not "{which}"'
            raise NotImplementedError(errormsg)
    to_plot = sc.odict(sc.dcp(to_plot)) # In case it's supplied as a dict

    n_rows = np.ceil(len(to_plot)/n_cols) # Number of subplot rows to have

    return to_plot, n_rows


def create_figs(args, font_size, font_family, sep_figs, fig=None):
    ''' Create the figures and set overall figure properties '''
    if sep_figs:
        fig = None
        figs = []
    else:
        if fig is None:
            fig = pl.figure(**args.fig) # Create the figure if none is supplied
        figs = None
    pl.subplots_adjust(**args.axis)
    pl.rcParams['font.size'] = font_size
    if font_family:
        pl.rcParams['font.family'] = font_family
    return fig, figs, None # Initialize axis to be None


def create_subplots(figs, fig, shareax, n_rows, n_cols, pnum, fig_args, sep_figs, log_scale, title):
    ''' Create subplots and set logarithmic scale '''

    # Try to find axes by label, if they've already been defined -- this is to avoid the deprecation warning of reusing axes
    label = f'ax{pnum+1}'
    ax = None
    try:
        for fig_ax in fig.axes:
            if fig_ax.get_label() == label:
                ax = fig_ax
                break
    except:
        pass

    # Handle separate figs
    if sep_figs:
        figs.append(pl.figure(**fig_args))
        if ax is None:
            ax = pl.subplot(111, label=label)
    else:
        if ax is None:
            ax = pl.subplot(n_rows, n_cols, pnum+1, sharex=shareax, label=label)

    # Handle log scale
    if log_scale:
        if isinstance(log_scale, list):
            if title in log_scale:
                ax.set_yscale('log')
        else:
            ax.set_yscale('log')

    return ax


def plot_data(sim, key, scatter_args):
    ''' Add data to the plot '''
    if sim.data is not None and key in sim.data and len(sim.data[key]):
        this_color = sim.results[key].color
        data_t = (sim.data.index-sim['start_day'])/np.timedelta64(1,'D') # Convert from data date to model output index based on model start date
        pl.scatter(data_t, sim.data[key], c=[this_color], **scatter_args)
        pl.scatter(pl.nan, pl.nan, c=[(0,0,0)], label='Data', **scatter_args)
    return


def plot_interventions(sim, ax):
    ''' Add interventions to the plot '''
    for intervention in sim['interventions']:
        intervention.plot(sim, ax)
    return


def title_grid_legend(ax, title, grid, commaticks, setylim, legend_args, show_legend=True):
    ''' Plot styling -- set the plot title, add a legend, and optionally add gridlines'''

    # Handle show_legend being in the legend args, since in some cases this is the only way it can get passed
    if 'show_legend' in legend_args:
        show_legend = legend_args.pop('show_legend')
        popped = True
    else:
        popped = False

    # Show the legend
    if show_legend:
        ax.legend(**legend_args)

    # If we removed it from the legend_args dict, put it back now
    if popped:
        legend_args['show_legend'] = show_legend

    # Set the title and gridlines
    ax.set_title(title)
    ax.grid(grid)

    # Set the y axis style
    if setylim:
        ax.set_ylim(bottom=0)
    if commaticks:
        ylims = ax.get_ylim()
        if ylims[1] >= 1000:
            sc.commaticks()

    return


def reset_ticks(ax, sim, interval, as_dates):
    ''' Set the tick marks, using dates by default '''

    # Set the x-axis intervals
    if interval:
        xmin,xmax = ax.get_xlim()
        ax.set_xticks(pl.arange(xmin, xmax+1, interval))

    # Set xticks as dates
    if as_dates:

        @ticker.FuncFormatter
        def date_formatter(x, pos):
            return (sim['start_day'] + dt.timedelta(days=x)).strftime('%b-%d')

        ax.xaxis.set_major_formatter(date_formatter)
        if not interval:
            ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    return


def tidy_up(fig, figs, sep_figs, do_save, fig_path, do_show, default_name='covasim.png'):
    ''' Handle saving, figure showing, and what value to return '''

    # Handle saving
    if do_save:
        if fig_path is None: # No figpath provided - see whether do_save is a figpath
            fig_path = default_name # Just give it a default name
        fig_path = sc.makefilepath(fig_path) # Ensure it's valid, including creating the folder
        pl.savefig(fig_path)

    # Show or close the figure
    if do_show:
        pl.show()
    else:
        pl.close(fig)

    # Return the figure or figures
    if sep_figs:
        return figs
    else:
        return fig


#%% Core plotting functions

def plot_sim(sim, to_plot=None, do_save=None, fig_path=None, fig_args=None, plot_args=None,
         scatter_args=None, axis_args=None, fill_args=None, legend_args=None, as_dates=True, dateformat=None,
         interval=None, n_cols=1, font_size=18, font_family=None, grid=False, commaticks=True, setylim=True,
         log_scale=False, colors=None, labels=None, do_show=True, sep_figs=False, fig=None):
    ''' Plot the results of a single simulation -- see Sim.plot() for documentation '''

    # Handle inputs
    args = handle_args(fig_args, plot_args, scatter_args, axis_args, fill_args, legend_args)
    to_plot, n_rows = handle_to_plot('sim', to_plot, n_cols)
    fig, figs, ax = create_figs(args, font_size, font_family, sep_figs, fig)

    # Do the plotting
    for pnum,title,keylabels in to_plot.enumitems():
        ax = create_subplots(figs, fig, ax, n_rows, n_cols, pnum, args.fig, sep_figs, log_scale, title)
        for reskey in keylabels:
            res = sim.results[reskey]
            res_t = sim.results['t']
            if colors is not None:
                color = colors[reskey]
            else:
                color = res.color
            if labels is not None:
                label = labels[reskey]
            else:
                label = res.name
            if res.low is not None and res.high is not None:
                ax.fill_between(res_t, res.low, res.high, color=color, **args.fill) # Create the uncertainty bound
            ax.plot(res_t, res.values, label=label, **args.plot, c=color)
            plot_data(sim, reskey, args.scatter) # Plot the data
            reset_ticks(ax, sim, interval, as_dates) # Optionally reset tick marks (useful for e.g. plotting weeks/months)
        plot_interventions(sim, ax) # Plot the interventions
        title_grid_legend(ax, title, grid, commaticks, setylim, args.legend) # Configure the title, grid, and legend

    return tidy_up(fig, figs, sep_figs, do_save, fig_path, do_show, default_name='covasim.png')


def plot_scens(scens, to_plot=None, do_save=None, fig_path=None, fig_args=None, plot_args=None,
         scatter_args=None, axis_args=None, fill_args=None, legend_args=None, as_dates=True, dateformat=None,
         interval=None, n_cols=1, font_size=18, font_family=None, grid=False, commaticks=True, setylim=True,
         log_scale=False, colors=None, labels=None, do_show=True, sep_figs=False, fig=None):
    ''' Plot the results of a scenario -- see Scenarios.plot() for documentation '''

    # Handle inputs
    args = handle_args(fig_args, plot_args, scatter_args, axis_args, fill_args, legend_args)
    to_plot, n_rows = handle_to_plot('scens', to_plot, n_cols)
    fig, figs, ax = create_figs(args, font_size, font_family, sep_figs, fig)

    # Do the plotting
    default_colors = sc.gridcolors(ncolors=len(scens.sims))
    for pnum,title,reskeys in to_plot.enumitems():
        ax = create_subplots(figs, fig, ax, n_rows, n_cols, pnum, args.fig, sep_figs, log_scale, title)
        for reskey in reskeys:
            resdata = scens.results[reskey]
            for snum,scenkey,scendata in resdata.enumitems():
                sim = scens.sims[scenkey][0] # Pull out the first sim in the list for this scenario
                res_y = scendata.best
                if colors is not None:
                    color = colors[scenkey]
                else:
                    color = default_colors[snum]
                if labels is not None:
                    label = labels[scenkey]
                else:
                    label = scendata.name
                ax.fill_between(scens.tvec, scendata.low, scendata.high, color=color, **args.fill) # Create the uncertainty bound
                ax.plot(scens.tvec, res_y, label=label, c=color, **args.plot) # Plot the actual line
                plot_data(sim, reskey, args.scatter) # Plot the data
                plot_interventions(sim, ax) # Plot the interventions
                reset_ticks(ax, sim, interval, as_dates) # Optionally reset tick marks (useful for e.g. plotting weeks/months)
        title_grid_legend(ax, title, grid, commaticks, setylim, args.legend, pnum==0) # Configure the title, grid, and legend -- only show legend for first

    return tidy_up(fig, figs, sep_figs, do_save, fig_path, do_show, default_name='covasim_scenarios.png')


def plot_result(sim, key, fig_args=None, plot_args=None, axis_args=None, scatter_args=None,
                font_size=18, font_family=None, grid=False, commaticks=True, setylim=True,
                as_dates=True, dateformat=None, interval=None, color=None, label=None, fig=None):
    ''' Plot a single result -- see Sim.plot_result() for documentation '''

    # Handle inputs
    fig_args  = sc.mergedicts({'figsize':(16,8)}, fig_args)
    axis_args = sc.mergedicts({'top': 0.95}, axis_args)
    args = handle_args(fig_args, plot_args, scatter_args, axis_args)
    fig, figs, ax = create_figs(args, font_size, font_family, sep_figs=False, fig=fig)

    # Gather results
    res = sim.results[key]
    res_t = sim.results['t']
    res_y = res.values
    if color is None:
        color = res.color

    # Reuse the figure, if available
    try:
        if fig.axes[0].get_label() == 'plot_result':
            ax = fig.axes[0]
    except:
        pass
    if ax is None: # Otherwise, make a new one
        ax = pl.subplot(111, label='plot_result')

    # Do the plotting
    if label is None:
        label = res.name
    ax.plot(res_t, res_y, c=color, label=label, **args.plot)
    plot_data(sim, key, args.scatter) # Plot the data
    plot_interventions(sim, ax) # Plot the interventions
    title_grid_legend(ax, res.name, grid, commaticks, setylim, args.legend) # Configure the title, grid, and legend
    reset_ticks(ax, sim, interval, as_dates) # Optionally reset tick marks (useful for e.g. plotting weeks/months)

    return fig


def plot_compare(df, log_scale=True, fig_args=None, plot_args=None, axis_args=None, scatter_args=None,
                font_size=18, font_family=None, grid=False, commaticks=True, setylim=True,
                as_dates=True, dateformat=None, interval=None, color=None, label=None, fig=None):
    ''' Plot a MultiSim comparison -- see MultiSim.plot_compare() for documentation '''

    # Handle inputs
    fig_args  = sc.mergedicts({'figsize':(16,16)}, fig_args)
    axis_args = sc.mergedicts({'left': 0.16, 'bottom': 0.05, 'right': 0.98, 'top': 0.98, 'wspace': 0.50, 'hspace': 0.10}, axis_args)
    args = handle_args(fig_args, plot_args, scatter_args, axis_args)
    fig, figs, ax = create_figs(args, font_size, font_family, sep_figs=False, fig=fig)

    # Map from results into different categories
    mapping = {
        'cum': 'Cumulative counts',
        'new': 'New counts',
        'n': 'Number in state',
        'r': 'R_eff',
        }
    category = []
    for v in df.index.values:
        v_type = v.split('_')[0]
        if v_type in mapping:
            category.append(v_type)
        else:
            category.append('other')
    df['category'] = category

    # Plot
    for i,m in enumerate(mapping):
        not_r_eff = m != 'r'
        if not_r_eff:
            ax = fig.add_subplot(2, 2, i+1)
        else:
            ax = fig.add_subplot(8, 2, 10)
        dfm = df[df['category'] == m]
        logx = not_r_eff and log_scale
        dfm.plot(ax=ax, kind='barh', logx=logx, legend=False)
        if not(not_r_eff):
            ax.legend(loc='upper left', bbox_to_anchor=(0,-0.3))
        ax.grid(True)

    return fig


#%% Transtree functions
def plot_transtree(self, *args, **kwargs):
    ''' Plot the transmission tree '''

    if self.detailed is None:
        errormsg = 'Please run sim.people.make_detailed_transtree() before calling plotting'
        raise ValueError(errormsg)

    ttlist = []
    for entry in self.detailed:
        if entry and entry.source:
            tdict = {
                'date': entry.date,
                'layer': entry.layer,
                's_asymp': entry.s.is_asymp,
                's_presymp': entry.s.is_presymp,
                's_sev': entry.s.is_severe,
                's_crit': entry.s.is_critical,
                's_diag': entry.s.is_diagnosed,
                's_quar': entry.s.is_quarantined,
                't_quar': entry.t.is_quarantined,
                     }
            ttlist.append(tdict)

    df = pd.DataFrame(ttlist).rename(columns={'date': 'Day'})
    df = df.loc[df['layer'] != 'seed_infection']

    df['Stage'] = 'Symptomatic'
    df.loc[df['s_asymp'], 'Stage'] = 'Asymptomatic'
    df.loc[df['s_presymp'], 'Stage'] = 'Presymptomatic'

    df['Severity'] = 'Mild'
    df.loc[df['s_sev'], 'Severity'] = 'Severe'
    df.loc[df['s_crit'], 'Severity'] = 'Critical'

    fig = pl.figure(figsize=(16,10))
    i=1; r=2; c=3

    def plot(key, title, i):
        dat = df.groupby(['Day', key]).size().unstack(key)
        ax = pl.subplot(r,c,i);
        dat.plot(ax=ax, legend=None)
        pl.legend(title=None)
        ax.set_title(title)

    to_plot = {
        'layer':'Layer',
        'Stage':'Source stage',
        's_diag':'Source diagnosed',
        's_quar':'Source quarantined',
        't_quar':'Target quarantined',
        'Severity':'Symptomatic source severity'
    }
    for i, (key, title) in enumerate(to_plot.items()):
        plot(key, title, i+1)

    return fig

def animate_transtree(transtree):
    colors = sc.vectocolor(sim.n, cmap='parula')

    msize = 10
    suscol = [0.5,0.5,0.5]
    plargs = dict(lw=2, alpha=0.5)
    idelay = 0.05
    daydelay = 0.2
    pl.rcParams['font.size'] = 18

    F = sc.objdict()
    T = sc.objdict()
    D = sc.objdict()
    Q = sc.objdict()

    for key in sims.keys():

        tt = tts[key]

        frames = [list() for i in range(sim.npts)]
        tests  = [list() for i in range(sim.npts)]
        diags  = [list() for i in range(sim.npts)]
        quars  = [list() for i in range(sim.npts)]

        for i,entry in enumerate(tt):
            frame = sc.objdict()
            dq = sc.objdict()
            if entry:
                source = entry['source']
                target = entry['target']
                target_date = entry['date']
                if source:
                    source_date = tt[source]['date']
                else:
                    source = 0
                    source_date = 0

                frame.x = [source_date, target_date]
                frame.y = [source, target]
                frame.c = colors[source] # colors[target_date]
                frame.e = True
                frames[target_date].append(frame)

                dq.t = target
                dq.d = target_date
                dq.c = colors[target]
                date_t = entry.t.date_tested
                date_d = entry.t.date_diagnosed
                date_q = entry.t.date_known_contact
                if ~np.isnan(date_t) and date_t<sim.npts: tests[int(date_t)].append(dq)
                if ~np.isnan(date_d) and date_d<sim.npts: diags[int(date_d)].append(dq)
                if ~np.isnan(date_q) and date_q<sim.npts: quars[int(date_q)].append(dq)
            else:
                frame.x = [0]
                frame.y = [i]
                frame.c = suscol
                frame.e = False
                frames[0].append(frame)

        F[key] = frames
        T[key] = tests
        D[key] = diags
        Q[key] = quars


    # Actually plot
    fig, axes = pl.subplots(figsize=(24,18), nrows=3, ncols=1)
    pl.subplots_adjust(**{'left': 0.10, 'bottom': 0.05, 'right': 0.85, 'top': 0.97, 'wspace': 0.25, 'hspace': 0.25})

    # Create the legend
    ax = pl.axes([0.85, 0.05, 0.14, 0.9])
    ax.axis('off')
    lcol = colors[0]
    pl.plot(np.nan, np.nan, '-', c=lcol, **plargs, label='Transmission')
    pl.plot(np.nan, np.nan, 'o', c=lcol, markersize=msize, **plargs, label='Source')
    pl.plot(np.nan, np.nan, '*', c=lcol, markersize=msize, **plargs, label='Target')
    pl.plot(np.nan, np.nan, 'o', c=lcol, markersize=msize*2, fillstyle='none', **plargs, label='Tested')
    pl.plot(np.nan, np.nan, 's', c=lcol, markersize=msize*1.2, **plargs, label='Diagnosed')
    pl.plot(np.nan, np.nan, 'x', c=lcol, markersize=msize*2.0, label='Known contact')
    pl.legend()


    for day in range(sim.npts):
        for i,key in enumerate(sims.keys()):
            pl.sca(axes[i])
            sim = sims[key]
            pl.title(f'Simulation: {labels[i]}; day: {day}; infections: {sim.results["cum_infections"][day]}')
            pl.xlim([0, sim.npts])
            pl.ylim([0, sim.n])
            pl.xlabel('Day')
            pl.ylabel('Person')
            flist = F[key][day]
            tlist = T[key][day]
            dlist = D[key][day]
            qlist = Q[key][day]
            if verbose: print(i, flist)
            for f in flist:
                if verbose: print(f)
                pl.plot(f.x[0], f.y[0], 'o', c=f.c, markersize=msize, **plargs)
                pl.plot(f.x, f.y, '-', c=f.c, **plargs)
            if animate_all:
                pl.pause(idelay)
            for f in flist:
                if f.e:
                    pl.plot(f.x[1], f.y[1], '*', c=f.c, markersize=msize, **plargs)
            if tlist:
                for dq in tlist:
                    pl.plot(dq.d, dq.t, 'o', c=dq.c, markersize=msize*2, fillstyle='none', **plargs)
            if dlist:
                for dq in dlist:
                    pl.plot(dq.d, dq.t, 's', c=dq.c, markersize=msize*1.2, **plargs)
            if qlist:
                for dq in qlist:
                    pl.plot(dq.d, dq.t, 'x', c=dq.c, markersize=msize*2.0)
            pl.plot([0, day], [0.5, 0.5], c='k', lw=5)
        if animate:
            pl.pause(daydelay)



#%% Plotly functions

def get_individual_states(sim):
    ''' Helper function to convert people into integers '''

    people = sim.people

    states = [
        {'name': 'Healthy',
         'quantity': None,
         'color': '#a6cee3',
         'value': 0
         },
        {'name': 'Exposed',
         'quantity': 'date_exposed',
         'color': '#ff7f00',
         'value': 2
         },
        {'name': 'Infectious',
         'quantity': 'date_infectious',
         'color': '#e33d3e',
         'value': 3
         },
        {'name': 'Recovered',
         'quantity': 'date_recovered',
         'color': '#3e89bc',
         'value': 4
         },
        {'name': 'Dead',
         'quantity': 'date_dead',
         'color': '#000000',
         'value': 5
         },
    ]

    z = np.zeros((len(people), sim.npts))
    for state in states:
        date = state['quantity']
        if date is not None:
            inds = sim.people.defined(date)
            for ind in inds:
                z[ind, int(people[date][ind]):] = state['value']

    return z, states


# Default settings for the Plotly legend
plotly_legend = dict(legend_orientation="h", legend=dict(x=0.0, y=1.18))

def plotly_sim(sim):
    ''' Main simulation results -- parallel of sim.plot() '''

    plots = []
    to_plot = cvd.get_sim_plots()
    for p,title,keylabels in to_plot.enumitems():
        fig = go.Figure()
        for key in keylabels:
            label = sim.results[key].name
            this_color = sim.results[key].color
            x = sim.results['date'][:]
            y = sim.results[key][:]
            fig.add_trace(go.Scatter(x=x, y=y, mode='lines', name=label, line_color=this_color))
            if sim.data is not None and key in sim.data:
                xdata = sim.data['date']
                ydata = sim.data[key]
                fig.add_trace(go.Scatter(x=xdata, y=ydata, mode='markers', name=label + ' (data)', line_color=this_color))

        if sim['interventions']:
            for interv in sim['interventions']:
                if hasattr(interv, 'days'):
                    for interv_day in interv.days:
                        if interv_day > 0 and interv_day < sim['n_days']:
                            fig.add_shape(dict(type="line", xref="x", yref="paper", x0=interv_day, x1=interv_day, y0=0, y1=1, name='Intervention', line=dict(width=0.5, dash='dash')))
                            fig.update_layout(annotations=[dict(x=interv_day, y=1.07, xref="x", yref="paper", text="Intervention change", showarrow=False)])

        fig.update_layout(title={'text':title}, yaxis_title='Count', autosize=True, **plotly_legend)

        plots.append(fig)
    return plots


def plotly_people(sim, do_show=False):
    ''' Plot a "cascade" of people moving through different states '''
    z, states = get_individual_states(sim)

    fig = go.Figure()

    for state in states[::-1]:  # Reverse order for plotting
        x = sim.results['date'][:]
        y = (z == state['value']).sum(axis=0)
        fig.add_trace(go.Scatter(
            x=x, y=y,
            stackgroup='one',
            line=dict(width=0.5, color=state['color']),
            fillcolor=state['color'],
            hoverinfo="y+name",
            name=state['name']
        ))

    if sim['interventions']:
        for interv in sim['interventions']:
                if hasattr(interv, 'days'):
                    if interv.do_plot:
                        for interv_day in interv.days:
                            if interv_day > 0 and interv_day < sim['n_days']:
                                fig.add_shape(dict(type="line", xref="x", yref="paper", x0=interv_day, x1=interv_day, y0=0, y1=1, name='Intervention', line=dict(width=0.5, dash='dash')))
                                fig.update_layout(annotations=[dict(x=interv_day, y=1.07, xref="x", yref="paper", text="Intervention change", showarrow=False)])

    fig.update_layout(yaxis_range=(0, sim.n))
    fig.update_layout(title={'text': 'Numbers of people by health state'}, yaxis_title='People', autosize=True, **plotly_legend)

    if do_show:
        fig.show()

    return fig


def plotly_animate(sim, do_show=False):
    ''' Plot an animation of each person in the sim '''

    z, states = get_individual_states(sim)

    min_color = min(states, key=lambda x: x['value'])['value']
    max_color = max(states, key=lambda x: x['value'])['value']
    colorscale = [[x['value'] / max_color, x['color']] for x in states]

    aspect = 5
    y_size = int(np.ceil((z.shape[0] / aspect) ** 0.5))
    x_size = int(np.ceil(aspect * y_size))

    z = np.pad(z, ((0, x_size * y_size - z.shape[0]), (0, 0)), mode='constant', constant_values=np.nan)

    days = sim.tvec

    fig_dict = {
        "data": [],
        "layout": {},
        "frames": []
    }

    fig_dict["layout"]["updatemenus"] = [
        {
            "buttons": [
                {
                    "args": [None, {"frame": {"duration": 200, "redraw": True},
                                    "fromcurrent": True}],
                    "label": "Play",
                    "method": "animate"
                },
                {
                    "args": [[None], {"frame": {"duration": 0, "redraw": True},
                                      "mode": "immediate",
                                      "transition": {"duration": 0}}],
                    "label": "Pause",
                    "method": "animate"
                }
            ],
            "direction": "left",
            "pad": {"r": 10, "t": 87},
            "showactive": False,
            "type": "buttons",
            "x": 0.1,
            "xanchor": "right",
            "y": 0,
            "yanchor": "top"
        }
    ]

    sliders_dict = {
        "active": 0,
        "yanchor": "top",
        "xanchor": "left",
        "currentvalue": {
            "font": {"size": 16},
            "prefix": "Day: ",
            "visible": True,
            "xanchor": "right"
        },
        "transition": {"duration": 200},
        "pad": {"b": 10, "t": 50},
        "len": 0.9,
        "x": 0.1,
        "y": 0,
        "steps": []
    }

    # make data
    fig_dict["data"] = [go.Heatmap(z=np.reshape(z[:, 0], (y_size, x_size)),
                                   zmin=min_color,
                                   zmax=max_color,
                                   colorscale=colorscale,
                                   showscale=False,
                                   )]

    for state in states:
        fig_dict["data"].append(go.Scatter(x=[None], y=[None], mode='markers',
                                           marker=dict(size=10, color=state['color']),
                                           showlegend=True, name=state['name']))

    # make frames
    for i, day in enumerate(days):
        frame = {"data": [go.Heatmap(z=np.reshape(z[:, i], (y_size, x_size)))],
                 "name": i}
        fig_dict["frames"].append(frame)
        slider_step = {"args": [
            [i],
            {"frame": {"duration": 5, "redraw": True},
             "mode": "immediate", }
        ],
            "label": i,
            "method": "animate"}
        sliders_dict["steps"].append(slider_step)

    fig_dict["layout"]["sliders"] = [sliders_dict]

    fig = go.Figure(fig_dict)

    fig.update_layout(
    autosize=True,
        xaxis=dict(
            showgrid=False,
            showline=False,
            showticklabels=False,
        ),
        yaxis=dict(
            automargin=True,
            showgrid=False,
            showline=False,
            showticklabels=False,
        ),
    )


    fig.update_layout(title={'text': 'Epidemic over time'}, **plotly_legend)

    if do_show:
        fig.show()

    return fig