# Thor-Base-Assembly
This project focuses on reverse engineering 3D geometry from STL files to recreate accurate parametric models. 
The process begins by converting the STL mesh into a solid body in Autodesk Fusion 360, enabling access to parametric features.
Key coordinates and dimensions of various sketch profiles and features—such as extrudes, cuts, and revolves—are then measured to replicate the original design. 
These feature details are fed into Antigravity, and with the assistance of Claude, a build123d script is generated. Running this script produces a reconstructed 3D model that closely matches the original geometry. 
To validate accuracy, the volume of the generated model is compared with the original using Fusion 360; the volumetric differences observed are 0.002 for Part 1, 0 for Parts 2 and 3, and 0.001 for Part 4, 0.005 for  Part 5 . The repository is organized into five part files, each containing four folders that include the original STL file, the generated output model, volumetric comparison results, and the corresponding code used for reconstruction.
