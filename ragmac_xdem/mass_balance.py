"""
Functions to calculate a glacier mass balance.
"""
import geoutils as gu
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xdem
from geoutils.georaster import RasterType
from scipy.interpolate import interp1d


def make_patch_spines_invisible(ax):
    ax.set_frame_on(True)
    ax.patch.set_visible(False)
    for sp in list(ax.spines.values()):
        sp.set_visible(False)


def make_spine_invisible(ax, direction):
    if direction in ["right", "left"]:
        ax.yaxis.set_ticks_position(direction)
        ax.yaxis.set_label_position(direction)
    elif direction in ["top", "bottom"]:
        ax.xaxis.set_ticks_position(direction)
        ax.xaxis.set_label_position(direction)
    else:
        raise ValueError("Unknown Direction : %s" % (direction,))
    ax.spines[direction].set_visible(True)


def ddem_bins_filtering(
    ddem_bins: pd.DataFrame, count_threshold: int = 10, nmad_fact: int = 5, verbose: bool = True
) -> pd.DataFrame:
    """
    Filter altitudinally averaged ddem bins (derived from xdem.volume.hypsometric_binning) based on count and distance to the median.

    :param ddem_bins: The ddem averaged by altitude bands.
    :param count_threshold: Minimum count in bin to be considered inlier. If <= 1, will be ignored.
    :param nmad_fact: Bins distant from the median of all bins by this factor times the NMAD of all bins will be discarded. If < 0, will be ignored.
    :param verbose: set to True to print some results to screen

    :returns: the filtered ddem_bins
    """
    # Copy to new DataFrame
    ddem_bins_filtered = ddem_bins.copy()

    # Exclude bins with low count
    if count_threshold > 1:
        outliers = ddem_bins_filtered["count"] < count_threshold
        ddem_bins_filtered.loc[outliers, "value"] = np.nan
        if verbose:
            print(f"Remove {np.sum(outliers)} outliers by count threshold")

    # Exclude bins larger than nmad_fact * NMAD
    # TODO: add iterations
    if nmad_fact > 0:
        outliers = np.abs(
            ddem_bins_filtered["value"] - np.median(ddem_bins_filtered["value"])
        ) > 5 * xdem.spatialstats.nmad(ddem_bins_filtered["value"])
        ddem_bins_filtered.loc[outliers, "value"] = np.nan
        if verbose:
            print(f"Remove {np.sum(outliers)} outliers by NMAD filter")

    return ddem_bins_filtered


def fill_ddem(
    ddem: RasterType, ddem_bins: pd.DataFrame, ref_dem: RasterType, roi_mask: np.ndarray = None
) -> RasterType:
    """
    Fill gaps in ddem with values interpolated from altitudinal bins in ddem_bins.

    :param ddem: the ddem to be filled
    :param ddem_bins: the altitudinally averaged ddem bins
    :param ref_dem: a reference elevation used for interpolating all pixels
    :param roi_mask: a mask of pixels to be interpolated
    """
    # Create a model for 2D interpolation
    gradient_model = interp1d(ddem_bins.index.mid, ddem_bins["value"].values, fill_value="extrapolate")

    # Convert ref_dem to an unmasked np.ndarray, needed for interp1d.
    ref_dem_array, ref_mask = gu.spatial_tools.get_array_and_mask(ref_dem)

    # Mask of pixels to be interpolated
    if roi_mask is None:
        mask = ddem.data.mask & ~ref_mask
    else:
        mask = roi_mask & ddem.data.mask & ~ref_mask

    # Fill ddem
    filled_ddem = ddem.copy()
    filled_ddem.data[mask] = gradient_model(ref_dem_array[mask.squeeze()])

    return filled_ddem


def mass_balance_local_hypso(ddem, ref_dem, roi_mask, plot=True, outfig=None):
    """
    Function to calculate the MB by filling gaps using a local hypsometric approach.


    """
    # Calculate mean elevation change within elevation bins
    # TODO: filter pixels within each bins that are outliers
    ddem_bins = xdem.volume.hypsometric_binning(ddem.data[roi_mask], ref_dem.data[roi_mask])

    # Filter outliers in bins
    ddem_bins_filtered = ddem_bins_filtering(ddem_bins, verbose=True)

    # Interpolate missing bins
    ddem_bins_filled = xdem.volume.interpolate_hypsometric_bins(ddem_bins_filtered, method="linear")

    # Create 2D filled dDEM
    ddem_filled = fill_ddem(ddem, ddem_bins_filled, ref_dem, roi_mask)

    # Calculate glacier area within those bins
    bins_area = xdem.volume.calculate_hypsometry_area(ddem_bins, ref_dem.data[roi_mask], pixel_size=ref_dem.res)
    obs_area = ddem_bins["count"] * ref_dem.res[0] * ref_dem.res[1]
    frac_obs = obs_area / bins_area

    # Calculate total volume change and mean dh
    dV = np.sum(ddem_bins_filled["value"].values * bins_area.values) / 1e9  # in km^3
    dh_mean = dV * 1e9 / bins_area.sum()

    # Plot
    if plot:
        bin_width = ddem_bins.index.left - ddem_bins.index.right

        plt.figure(figsize=(18, 6))

        # Hypsometric curve
        ax1 = plt.subplot(131)
        p1 = plt.plot(ddem_bins["value"], ddem_bins.index.mid, linestyle="-", zorder=1, label="Raw ddem bins")
        p1b = plt.plot(
            ddem_bins_filled["value"],
            ddem_bins.index.mid,
            linestyle=":",
            zorder=1,
            label="Filtered + interpolated ddem bins",
        )
        plt.xlabel("Elevation change (m)")
        plt.ylabel("Elevation (m)")
        plt.legend()

        ax2 = ax1.twiny()
        p2 = plt.barh(y=ddem_bins.index.mid, width=bins_area / 1e6, height=bin_width, zorder=2, alpha=0.4)
        plt.xlabel("Glacier area per elevation bins (km\u00b2)")

        ax3 = ax1.twiny()
        ax3.spines["top"].set_position(("axes", 1.1))
        make_patch_spines_invisible(ax3)
        make_spine_invisible(ax3, "top")
        p3 = plt.barh(y=ddem_bins.index.mid, width=frac_obs, height=bin_width, zorder=2, alpha=0.4, color="gray")
        plt.xlabel("Fraction of observations")

        plt.tight_layout()

        # Set ticks color
        tkw = dict(size=4, width=1.5)
        ax1.tick_params(axis="x", colors=p1[0].get_color(), **tkw)
        ax2.tick_params(axis="x", colors=p2.patches[0].get_facecolor(), **tkw)
        ax3.tick_params(axis="x", colors=p3.patches[0].get_facecolor(), **tkw)

        # ddem before interpolation
        ax2 = plt.subplot(132)
        ddem.show(ax=ax2, cmap="coolwarm_r", vmin=-50, vmax=50)
        plt.title("dDEM before interpolation")

        # ddem before interpolation
        ax3 = plt.subplot(133, sharex=ax2, sharey=ax2)
        ddem_filled.show(ax=ax3, cmap="coolwarm_r", vmin=-50, vmax=50)
        plt.title("dDEM after interpolation")

        if outfig is None:
            plt.show()
        else:
            plt.savefig(outfig, dpi=200)
            plt.close()

    return ddem_bins, bins_area, frac_obs, dV, dh_mean
