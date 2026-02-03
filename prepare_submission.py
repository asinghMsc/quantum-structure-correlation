import os
import zipfile
import shutil

def prepare_package():
    # Define files to include (Source only for arXiv)
    files_to_include = [
        'manuscript.tex',
        'references.bib'
    ]
    
    # Target folder and zip name
    submission_folder = 'arxiv_manuscript'
    zip_name = 'arxiv_submission_Singh.zip'
    
    print(f"--- Preparing arXiv Manuscript Package ---")
    
    # Create clean directory
    if os.path.exists(submission_folder):
        shutil.rmtree(submission_folder)
    os.makedirs(submission_folder)
    
    # Copy files
    for file in files_to_include:
        if os.path.exists(file):
            shutil.copy(file, os.path.join(submission_folder, file))
            print(f"Added: {file}")
        else:
            print(f"WARNING: {file} not found!")

    # Create ZIP
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in files_to_include:
            if os.path.exists(os.path.join(submission_folder, file)):
                zipf.write(os.path.join(submission_folder, file), file)
    
    print(f"--- SUCCESS ---")
    print(f"ZIP created: {zip_name}")
    print(f"This ZIP contains only your LaTeX source and Bibliography.")

if __name__ == "__main__":
    prepare_package()
