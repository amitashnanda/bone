import pandas as pd
import numpy as np
import scanpy as sc
import tarfile
import os
import re


def log2(expr: pd.DataFrame):
    expr = np.log2(expr + 1)
    return expr


def normalize(
    expr: pd.DataFrame, norm_type: str = "cpm", log2: bool = False
) -> pd.DataFrame:
    """Normalize given expression file via scanpy preprocessing

    Args:
        expr (pd.DataFrame): Expression file to be normalized
        norm_type (str, optional): Normalization method. Defaults to "cpm".
        log2 (bool, optional): Take log2 of all values after normalization. Defaults to False.

    Raises:
        ValueError: Only cpm normalization is currently available

    Returns:
        pd.DataFrame: Normalized expression dataframe
    """
    if norm_type.lower() != "cpm":
        raise ValueError(f"{norm_type} normalization not available. Please use 'cpm'")
    elif norm_type.lower == "cpm":
        norm_type = 1e6

    adata = sc.AnnData(expr.T)
    # 1e6 = counts per million (cpm) normalization
    sc.pp.normalize_total(adata, target_sum=norm_type)
    sc.pp.log1p(adata, base=2)
    expr = adata.to_df().T

    if log2:
        expr = np.log2(expr + 1)
    return expr


def read_raw(tar_file: str, **kwargs) -> pd.DataFrame:
    """Parse tar file into expression frame

    Args:
        tar_file (str): path to tarfile

    Raises:
        ValueError: **kwargs must clean tarfile to a two column frame with ID and expression value

    Returns:
        pd.DataFrame: Expression dataframe
    """
    tar_dir = tar_file.split(".")[0]
    if not os.path.exists(tar_dir):
        with tarfile.open(tar_file) as tar:
            tar.extractall(tar_dir)

    if "sep" not in kwargs:
        kwargs["sep"] = "\t"

    for file in os.listdir(tar_dir):
        gsm = re.sub(".*(GSM[0-9]+).*", "\\1", file)
        filepath = os.path.join(tar_dir, file)
        gsm_df = pd.read_csv(filepath, **kwargs)
        try:
            gsm_df.columns = ["ID", gsm]
        except:
            raise ValueError(
                "gsm_df should only contain ID column and read data. Enter **kwargs for pd.read_csv() clean"
            )
        gsm_df = gsm_df.set_index("ID")
        if "df" not in locals():
            df = gsm_df
        else:
            df = df.merge(gsm_df, left_index=True, right_index=True)
    return df


def add_probeID(expr: pd.DataFrame, probe_type: str) -> pd.DataFrame:
    """Only RNAseq. Add an index level of ProbeID. ProbeID will be merged with existing index

    Args:
        expr (pd.DataFrame): Expression file to parse
        organism (str): Type of organism for reference probe
        probe_type (str): Probe type to use for ProbeID values

    Raises:
        ValueError: Only certain probe types are currently available

    Returns:
        pd.DataFrame: Frame with ProbeID in index
    """
    file_path = os.path.dirname(os.path.abspath(__file__))
    homo_sapiens = os.path.join(file_path, "references/homo_sapiens.csv")
    mus_musculus = os.path.join(file_path, "references/mus_musculus.csv")

    probe_type = probe_type.upper()
    if probe_type not in ["ENST", "ENSG", "ENSMUST", "ENSMUSG"]:
        raise ValueError("Only 'ENST', 'ENSG', 'ENSMUST', or 'ENSMUSG' are available.")
    elif probe_type in ["ENST", "ENSG"]:
        probe_df = pd.read_csv(homo_sapiens, index_col=0)[probe_type]
        probe_df = probe_df[~probe_df.index.duplicated(keep="first")]
        expr = expr.merge(probe_df, how="left", right_index=True, left_index=True)
    elif probe_type in ["ENSMUST", "ENSMUSG"]:
        probe_df = pd.read_csv(mus_musculus, index_col=0)[probe_type]
        probe_df = probe_df[~probe_df.index.duplicated(keep="first")]
        expr = expr.merge(probe_df, how="left", right_index=True, left_index=True)

    expr = expr.rename(columns={probe_type: "ProbeID"})
    if expr.index.name:
        current_index = [expr.index.name]
    elif expr.index.names:
        current_index = expr.index.names
    expr = expr.reset_index()
    expr = expr.set_index(["ProbeID"] + current_index)
    return expr
