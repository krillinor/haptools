from __future__ import annotations
import logging

from haptools import data
from .haplotype import HaptoolsHaplotype


def transform_haps(
    genotypes: Path,
    haplotypes: Path,
    region: str = None,
    samples: list[str] = None,
    output: Path = Path("-"),
    log: Logger = None,
):
    """
    Creates a VCF composed of haplotypes

    Parameters
    ----------
    genotypes : Path
        The path to the genotypes in VCF format
    haplotypes : Path
        The path to the haplotypes in a .hap file
    region : str, optional
        See documentation for :py:meth:`~.data.Genotypes.read`
        and :py:meth:`~.data.Haplotypes.read`
    samples : list[str], optional
        See documentation for :py:meth:`~.data.Genotypes.read`
    output : Path, optional
        The location to which to write output
    log : Logger, optional
        A logging module to which to write messages about progress and any errors
    """
    if log is None:
        log = logging.getLogger("run")
        logging.basicConfig(
            format="[%(levelname)8s] %(message)s (%(filename)s:%(lineno)s)",
            level="ERROR",
        )

    log.info("Loading haplotypes")
    hp = data.Haplotypes(haplotypes, log=log)
    hp.read(region=region)

    log.info("Extracting variants from haplotypes")
    variants = {var.id for hap in hp.data.values() for var in hap.variants}

    log.info("Loading genotypes")
    gt = data.GenotypesRefAlt(genotypes, log=log)
    # gt._prephased = True
    gt.read(region=region, samples=samples, variants=variants)
    gt.check_missing()
    gt.check_biallelic()
    gt.check_phase()

    log.info("Transforming genotypes via haplotypes")
    hp_gt = data.GenotypesRefAlt(fname=output, log=log)
    hp.transform(gt, hp_gt)

    log.info("Writing haplotypes to VCF")
    hp_gt.write()

    return hp_gt
