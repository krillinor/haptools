from __future__ import annotations
import logging
from pathlib import Path

from haptools import data


class GenotypesAncestry(data.GenotypesRefAlt):
    """
    Extends the GenotypesRefAlt class for ancestry data

    The ancestry information is stored within the FORMAT field of the VCF

    Attributes
    ----------
    data : np.array
        See documentation for :py:attr:`~.Genotypes.data`
    fname : Path | str
        See documentation for :py:attr:`~.Genotypes.fname`
    samples : tuple[str]
        See documentation for :py:attr:`~.Genotypes.samples`
    variants : np.array
        See documentation for :py:attr:`~.GenotypesRefAlt.variants`
    ancestry : np.array
        The ancestral population of each allele in each sample of
        :py:attr:`~.GenotypesAncestry.data`
    log: Logger
        See documentation for :py:attr:`~.Genotypes.log`
    """
    def __init__(self, fname: Path | str, log: Logger = None):
        super().__init__(fname, log)
        self.ancestry = None

    def _iterate(self, vcf: VCF, region: str = None, variants: set[str] = None):
        """
        See documentation for :py:meth:`~.Genotypes._iterate`
        """
        pass

    def read(
        self,
        region: str = None,
        samples: list[str] = None,
        variants: set[str] = None,
        max_variants: int = None,
    ):
        """
        See documentation for :py:meth:`~.Genotypes.read`
        """
        pass

    def subset(
        self,
        samples: tuple[str] = None,
        variants: tuple[str] = None,
        inplace: bool = False,
    ):
        """
        See documentation for :py:meth:`~.Genotypes.subset`
        """
        pass

    def check_missing(self, discard_also=False):
        """
        See documentation for :py:meth:`~.Genotypes.check_missing`
        """
        pass

    def check_biallelic(self, discard_also=False):
        """
        See documentation for :py:meth:`~.Genotypes.check_biallelic`
        """
        pass

    def write(self):
        raise ValueError("Not implemented")


def transform_haps(
    genotypes: Path,
    haplotypes: Path,
    region: str = None,
    samples: list[str] = None,
    haplotype_ids: set[str] = None,
    chunk_size: int = None,
    haps_chunk_size: int = None,
    discard_missing: bool = False,
    output: Path = Path("-"),
    log: Logger = None,
):
    """
    Creates a VCF composed of haplotypes

    Parameters
    ----------
    genotypes : Path
        The path to the genotypes
    haplotypes : Path
        The path to the haplotypes in a .hap file
    region : str, optional
        See documentation for :py:meth:`~.data.Genotypes.read`
        and :py:meth:`~.data.Haplotypes.read`
    samples : list[str], optional
        See documentation for :py:meth:`~.data.Genotypes.read`
    haplotype_ids: set[str], optional
        A set of haplotype IDs to obtain from the .hap file. All others are ignored.

        If not provided, all haplotypes will be used.
    chunk_size: int, optional
        The max number of variants to fetch from the PGEN file at any given time

        If this value is provided, variants from the PGEN file will be loaded in
        chunks so as to use less memory. This argument is ignored if the genotypes are
        not in PGEN format.
    haps_chunk_size: int, optional
        The max number of haplotypes to transform together at any given time

        If this value is provided, haplotypes from the .hap file will be transformed in
        chunks so as to use less memory.
    discard_missing : bool, optional
        Discard any samples that are missing any of the required genotypes

        The default is simply to complain about it
    output : Path, optional
        The location to which to write output
    log : Logger, optional
        A logging module to which to write messages about progress and any errors
    """
    if log is None:
        log = logging.getLogger("haptools transform")
        logging.basicConfig(
            format="[%(levelname)8s] %(message)s (%(filename)s:%(lineno)s)",
            level="ERROR",
        )

    log.info("Loading haplotypes")
    hp = data.Haplotypes(haplotypes, log=log)
    hp.read(region=region, haplotypes=haplotype_ids)

    # check that all of the haplotypes were loaded successfully and warn otherwise
    if haplotype_ids is not None and len(haplotype_ids) > len(hp.data):
        diff = list(haplotype_ids.difference(hp.data.keys()))
        first_few = 5 if len(diff) > 5 else len(diff)
        log.warning(
            f"{len(diff)} haplotypes could not be found in the .hap file. Check "
            "that the IDs in your .hap file correspond with those you provided. "
            f"Here are the first few missing haplotypes: {diff[:first_few]}"
        )

    log.info("Extracting variants from haplotypes")
    variants = {var.id for hap in hp.data.values() for var in hap.variants}

    if genotypes.suffix == ".pgen":
        log.info("Loading genotypes from PGEN file")
        gt = data.GenotypesPLINK(fname=genotypes, log=log, chunk_size=chunk_size)
    else:
        log.info("Loading genotypes from VCF/BCF file")
        gt = data.GenotypesRefAlt(fname=genotypes, log=log)
    # gt._prephased = True
    gt.read(region=region, samples=samples, variants=variants)
    gt.check_missing(discard_also=discard_missing)
    gt.check_biallelic()
    gt.check_phase()

    # check that all of the variants were loaded successfully and warn otherwise
    if len(variants) < len(gt.variants):
        diff = list(variants.difference(gt.variants["id"]))
        first_few = 5 if len(diff) > 5 else len(diff)
        log.warning(
            f"{len(diff)} variants could not be found in the genotypes file. Check "
            "that the IDs in your .hap file correspond with those in the genotypes "
            f"file. Here are the first few missing variants: {diff[:first_few]}"
        )

    if output.suffix == ".pgen":
        out_file_type = "PGEN"
        hp_gt = data.GenotypesPLINK(fname=output, log=log, chunk_size=chunk_size)
    else:
        out_file_type = "VCF/BCF"
        hp_gt = data.GenotypesRefAlt(fname=output, log=log)
    log.info("Transforming genotypes via haplotypes")
    hp.transform(gt, hp_gt, chunk_size=haps_chunk_size)

    log.info(f"Writing haplotypes to {out_file_type} file")
    hp_gt.write()

    return hp_gt
