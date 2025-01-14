"""plotting functions"""

import geopandas as gpd
import matplotlib
import numpy as np
from IPython.display import HTML
from matplotlib import animation
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D
from mpl_toolkits.axes_grid1 import make_axes_locatable

"""
@author: friedrichknuth
"""


def plot_array_gallery(array_3d, titles_list=None, figsize=(10, 15), vmin=None, vmax=None, cmap="viridis"):

    if not vmin:
        vmin = np.nanmin(array_3d) + 50
    if not vmax:
        vmax = np.nanmax(array_3d) - 50

    rows, columns = get_row_column(len(array_3d))
    fig = plt.figure(figsize=(10, 15))

    for i in range(rows * columns):
        try:
            array = array_3d[i]
            ax = plt.subplot(rows, columns, i + 1, aspect="auto")
            ax.imshow(array, interpolation="none", cmap=cmap, vmin=vmin, vmax=vmax)
            ax.set_xticks(())
            ax.set_yticks(())
            if titles_list:
                ax.set_title(titles_list[i])
        except:
            pass
    plt.tight_layout()


def plot_time_series_gallery(
    x_values,
    y_values,
    labels=None,
    predictions_df_list=None,
    std_df_list=None,
    x_ticks_off=False,
    y_ticks_off=False,
    sharex=True,
    figsize=(15, 10),
    legend=True,
    linestyle="none",
    legend_labels=[
        "Observations",
    ],
):

    rows, columns = get_row_column(len(x_values))

    fig = plt.figure(figsize=figsize)
    axes = []
    for i in range(rows * columns):
        try:
            x, y = x_values[i], y_values[i]
            ax = plt.subplot(rows, columns, i + 1, aspect="auto")
            ax.plot(x, y, marker="o", c="b", linestyle=linestyle, label=legend_labels[0])
            if x_ticks_off:
                ax.set_xticks(())
            if y_ticks_off:
                ax.set_yticks(())
            axes.append(ax)
        except:
            pass
    if not isinstance(predictions_df_list, type(None)):
        for idx, df in enumerate(predictions_df_list):
            try:
                std_df = std_df_list[idx]
            except:
                std_df = None

            for i, series in df.iteritems():
                ax = axes[i]
                try:
                    series.plot(ax=ax, c="C" + str(idx + 1), label=legend_labels[idx + 1])
                except:
                    series.plot(ax=ax, c="C" + str(idx + 1), label="Observations")
                if not isinstance(std_df, type(None)):
                    x = series.index.values
                    y = series.values
                    std_prediction = std_df[i].values
                    ax.fill_between(
                        x,
                        y - 1.96 * std_prediction,
                        y + 1.96 * std_prediction,
                        alpha=0.2,
                        label=legend_labels[idx + 1] + "_95_%conf",
                        color="C" + str(idx + 1),
                    )

    if labels:
        for i, ax in enumerate(axes):
            ax.set_title(labels[i])

    if legend:
        axes[0].legend()
    if sharex:
        for ax in axes[:-columns]:
            ax.set_xticks(())
    plt.tight_layout()


def plot_timelapse(
    array, figsize=(10, 10), points=None, titles_list=None, frame_rate=200, vmin=None, vmax=None, alpha=None
):
    """
    array with shape (time, x, y)
    """
    if not vmin:
        vmin = np.nanmin(array) + 50
    if not vmax:
        vmax = np.nanmax(array) - 50

    fig, ax = plt.subplots(figsize=(10, 10))
    im = ax.imshow(array[0, :, :], interpolation="none", alpha=alpha, vmin=vmin, vmax=vmax)
    if points:
        (p,) = ax.plot(points[0], points[1], marker="o", color="b", linestyle="none")
    plt.close()

    def vid_init():
        im.set_data(array[0, :, :])
        if points:
            p.set_data(points[0], points[1])

    def vid_animate(i):
        im.set_data(array[i, :, :])
        if points:
            p.set_data(points[0], points[1])
        if titles_list:
            ax.set_title(titles_list[i])

    anim = animation.FuncAnimation(fig, vid_animate, init_func=vid_init, frames=array.shape[0], interval=frame_rate)
    return HTML(anim.to_html5_video())


def plot_count_std(
    count_nmad_ma_stack,
    count_vmin=1,
    count_vmax=50,
    count_cmap="gnuplot",
    std_vmin=0,
    std_vmax=20,
    std_cmap="cividis",
    points=None,
    alpha=None,
    ticks_off=False,
):

    fig, axes = plt.subplots(1, 2, figsize=(15, 10))

    ax = axes[0]
    cmap = plt.cm.get_cmap(count_cmap, count_vmax)
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.05)

    plt.colorbar(
        ax.imshow(
            count_nmad_ma_stack[0], vmin=count_vmin, vmax=count_vmax, interpolation="none", cmap=cmap, alpha=alpha
        ),
        cax=cax,
        extend="max",
    ).set_label(label="DEM count", size=12)
    if points:
        (p,) = ax.plot(points[0], points[1], marker="o", color="b", linestyle="none")
        legend_elements = []
        legend_elements.append(Line2D([0], [0], color="b", label="Observations", marker="o", linestyle="none"))
        ax.legend(handles=legend_elements, loc="best")

    ax = axes[1]
    cmap = plt.cm.get_cmap(std_cmap)

    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.05)

    plt.colorbar(
        ax.imshow(count_nmad_ma_stack[1], vmin=std_vmin, vmax=std_vmax, interpolation="none", alpha=alpha, cmap=cmap),
        cax=cax,
        extend="max",
    ).set_label(label="STD [m]", size=12)

    if points:
        (p,) = ax.plot(points[0], points[1], marker="o", color="b", linestyle="none")

    if ticks_off:
        for ax in axes:
            ax.set_xticks(())
            ax.set_yticks(())


def xr_plot_count_std_glacier(
    count_da,
    std_da,
    glacier_gdf=None,
    flowline_gdf=None,
    points=None,
    plot_to_glacier_extent=False,
    count_vmin=1,
    count_vmax=50,
    count_cmap="gnuplot",
    std_vmin=0,
    std_vmax=20,
    std_cmap="cividis",
    alpha=None,
    ticks_off=False,
):
    fig, axes = plt.subplots(1, 2, figsize=(15, 10))

    ax = axes[0]
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.05)
    cmap = plt.cm.get_cmap(count_cmap, count_vmax)
    norm = matplotlib.colors.Normalize(vmin=count_vmin, vmax=count_vmax)
    cbar = matplotlib.colorbar.ColorbarBase(cax, cmap=cmap, norm=norm, extend="max", alpha=alpha)
    cbar.set_label(label="DEM count", size=12)
    count_da.plot(ax=ax, cmap=cmap, add_colorbar=False, alpha=alpha, vmin=count_vmin, vmax=count_vmax)

    legend_elements = []
    if isinstance(glacier_gdf, type(gpd.GeoDataFrame())):
        legend_elements.append(Line2D([0], [0], color="k", label="Glacier Outline"))
    if isinstance(flowline_gdf, type(gpd.GeoDataFrame())):
        legend_elements.append(Line2D([0], [0], color="orange", label="Flowlines"))
    if points:
        legend_elements.append(Line2D([0], [0], color="b", label="Observations", marker="o", linestyle="none"))
    if legend_elements:
        ax.legend(handles=legend_elements, loc="best")

    ax = axes[1]
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.05)
    cmap = plt.cm.get_cmap(std_cmap)
    norm = matplotlib.colors.Normalize(vmin=std_vmin, vmax=std_vmax)
    cbar = matplotlib.colorbar.ColorbarBase(cax, cmap=cmap, norm=norm, extend="max", alpha=alpha)
    cbar.set_alpha(alpha)  # not sure why this doesn't work....
    cbar.set_label(label="STD [m]", size=12)
    std_da.plot(ax=ax, cmap=cmap, add_colorbar=False, alpha=alpha, vmin=std_vmin, vmax=std_vmax)

    if ticks_off:
        for ax in axes:
            ax.set_xticks(())
            ax.set_yticks(())

    for ax in axes:
        ax.set_title("")
        if points:
            (p,) = ax.plot(points[0], points[1], marker="o", color="b", linestyle="none")
        if isinstance(glacier_gdf, type(gpd.GeoDataFrame())):
            glacier_gdf.plot(ax=ax, facecolor="none", legend=True)
        if isinstance(flowline_gdf, type(gpd.GeoDataFrame())):
            flowline_gdf.plot(ax=ax, color="orange", legend=True)
        if plot_to_glacier_extent:
            glacier_bounds = glacier_gdf.bounds.values[0]
            ax.set_xlim(glacier_bounds[0], glacier_bounds[2])
            ax.set_ylim(glacier_bounds[1], glacier_bounds[3])


###########  Miscellaneous
def check_if_number_even(n):
    """
    checks if int n is an even number
    """
    if (n % 2) == 0:
        return True
    else:
        return False


def make_number_even(n):
    """
    adds 1 to int n if odd number
    """
    if check_if_number_even(n):
        return n
    else:
        return n + 1


def get_row_column(n):
    """
    returns largest factor pair for int n
    makes rows the larger number
    """
    max_pair = max([(i, n / i) for i in range(1, int(n ** 0.5) + 1) if n % i == 0])
    rows = int(max(max_pair))
    columns = int(min(max_pair))

    # in case n is odd
    # check if you get a smaller pair by adding 1 to make number even
    if not check_if_number_even(n):
        n = make_number_even(n)
        max_pair = max([(i, n / i) for i in range(1, int(n ** 0.5) + 1) if n % i == 0])
        alt_rows = int(max(max_pair))
        alt_columns = int(min(max_pair))

        if (rows, columns) > (alt_rows, alt_columns):
            return (alt_rows, alt_columns)
        else:
            return (rows, columns)
    return (rows, columns)


def float_x_y_to_int_tuple(x_floats, y_floats):
    """
    Used to create labels for time series plots
    """
    x_int = [int(i) for i in x_floats]
    y_int = [int(i) for i in y_floats]
    x_y_tuples = list(zip(x_int, y_int))
    return x_y_tuples
