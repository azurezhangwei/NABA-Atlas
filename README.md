# NABA-Atlas

Comparing white matter (WM) connections between adults and neonates using diffusion MRI (dMRI) can enhance our understanding of typical brain development and help identify potential biomarkers for neurological disorders. Brain WM atlases are valuable tools for facilitating population-wise comparisons, allowing for the identification of WM differences between adult and neonatal brains. Currently, existing studies typically rely on atlases created for a specific population (either neonates or adults), where each atlas resides in its own space, preventing direct comparisons across populations.

A cross-population WM atlas, created using both adult and neonatal imaging data, that allows for the concurrent mapping of brain connections in the two populations is still lacking. Therefore, in this study, we propose the neonatal/adult brain atlas, namely NABA, a WM tractography atlas that is built using dMRI data from both neonates and adults. NABA is created using a robust, data-driven tractography fiber clustering pipeline, allowing for group-wise WM atlasing across diverse populations, despite potential anatomical variability in the WM. This atlas serves as a standardized template for parcellating WM tractography in new individuals, enabling direct comparisons of WM tracts across the two populations. With the atlas, we perform a comparative study to examine the WM development of the neonates in comparison to the adult data. Our study encompasses four key analyses: (1) evaluating the feasibility of joint WM mapping between neonatal and adult brains using the atlas, (2) characterizing the development of the WM in different neonatal ages compared with adults, (3) assessing sex-related differences in neonatal WM development, and (4) investigating the effects of preterm birth on neonatal WM development. There are several key observations from our study. First, we demonstrate NABA's advantages in identifying fiber tracts across both populations, with strong adaptability to age-specific anatomical variability. Furthermore, we observe rapid fractional anisotropy (FA) development in long-range association tracts, including the arcuate fasciculus and superior longitudinal fasciculus II, while intra-cerebellar tracts exhibit slower development in neonates. Third, neonatal females display overall faster FA development compared to males. Fourth, although preterm neonates exhibit a generally lower FA development rate than full-term infants, they show relatively higher FA growth rates in tracts, including the corticospinal tract, corona radiata-pontine pathway, and intracerebellar tracts. Overall, we show that the atlas can be a useful tool to investigate the WM development in neonates and adults.

## Repo layout

- `NABA-Atlas/`: Atlas data (large `.vtk`/`.vtp` files excluded from git)
  - `NABA-RegAtlas/registration_atlas.vtk`
  - `NABA-800FC/atlas.p`, `NABA-800FC/atlas.vtp`, tract MRMLs
- `inference/run_naba_inference.py`: Unified inference script

## Requirements

- White Matter Analysis (WMA) Python library: https://github.com/SlicerDMRI/whitematteranalysis
- 3D Slicer: https://download.slicer.org/
- NABA-Atlas data files (large atlas files are excluded from git; Zenodo link [TBD](https://doi.org/10.5281/zenodo.18227691))

## Parcellation usage

```bash
python inference/run_naba_inference.py -i /path/to/input.vtk -o /path/to/output \
  -a /path/to/NABA-Atlas -s /path/to/Slicer -n 20 -x 1 \
  -m "/path/to/Slicer --launch /path/to/FiberTractMeasurements"
```

Parameters:

- `-i`: Input tractography data (.vtk/.vtp) in RAS coordinates.
- `-o`: Output directory root (case subfolder is created).
- `-a`: Atlas root (expects NABA/ORG reg + 800FC folders).
- `-s`: 3D Slicer executable path.
- `-t`: Optional transform to match subject to atlas size.
- `-r`: Registration mode (rig or nonrig).
- `-n`: Number of threads (>=1).
- `-x`: Use virtual X server via xvfb-run (0/1).
- `-d`: Export diffusion measurements (0/1).
- `-m`: FiberTractMeasurements CLI module path.
- `-c`: Clean temporary files (0 keep, 1 minimal, 2 maximal).

## Output structure

Example output structure (case ID shown as `CASE_ID`):

- `OUTPUT_DIR/CASE_ID/`
- `OUTPUT_DIR/CASE_ID/AnatomicalTracts/`
- `OUTPUT_DIR/CASE_ID/FiberClustering/InitialClusters/`
- `OUTPUT_DIR/CASE_ID/FiberClustering/OutlierRemovedClusters/`
- `OUTPUT_DIR/CASE_ID/FiberClustering/TransformedClusters/CASE_ID/`
- `OUTPUT_DIR/CASE_ID/FiberClustering/SeparatedClusters/`
- `OUTPUT_DIR/CASE_ID/InvTransformedTracts/` (only when `-t` is used)
- `OUTPUT_DIR/CASE_ID/TractRegistration/`
- `OUTPUT_DIR/CASE_ID/TransformedTracts/` (only when `-t` is used)

When `-d 1` is set:
- `OUTPUT_DIR/CASE_ID/FiberClustering/SeparatedClusters/diffusion_measurements_commissural.csv`
- `OUTPUT_DIR/CASE_ID/FiberClustering/SeparatedClusters/diffusion_measurements_left.csv`
- `OUTPUT_DIR/CASE_ID/FiberClustering/SeparatedClusters/diffusion_measurements_right.csv`
- `OUTPUT_DIR/CASE_ID/AnatomicalTracts/diffusion_measurements_anatomical_tracts.csv`

## How to cite

Zhang, W., Li, Y., Zheng, R., Sochen, N. A., Chen, Y., Zekelman, L. R., ... & Zhang, F. (2025). Cross-Population White Matter Atlas Creation for Concurrent Mapping of Brain Connections in Neonates and Adults with Diffusion MRI Tractography. arXiv preprint arXiv:2512.20370.
