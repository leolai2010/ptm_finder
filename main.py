##!/usr/bin/env python
# Import necessary libraries
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import re
import numpy as np
import pandas as pd
import time
import os 

# Function for parsing sequence in FASTA file into a Python dictionary relying on BioPython library
def parseFASTA(fasta_file):
    protein_sequences = {}
    try:
        sequence = re.compile("(>.*?)\n([A-Z\n]*)", re.DOTALL)
        fasta_file = fasta_file.decode('utf-8').strip().replace("\r\n", "\n")
        for protein_name in re.findall(sequence, fasta_file):
                protein_sequences[protein_name[0]] = protein_name[1].replace('\n', '')
        return protein_sequences
    except EOFError:
        print("Unable to parse FASTA file") 
        return False

# Function for parsing peptide names from TSV file into a Python dictionary
def parseTSV(tsv_file):
    peptide_unimod_sequences = []
    peptide_sequences = {}    
    position_regex = "(\(UniMod:\d*\))"
    try:
        tsv_file = tsv_file.decode('utf-8').strip().replace("\r\n", "\n").split()
        for ptm_unimod in tsv_file:
            peptide_unimod = re.findall(position_regex, ptm_unimod)
            if peptide_unimod:
                peptide_unimod_sequences.append(ptm_unimod)
        peptide_unimod_sequences = list(dict.fromkeys(peptide_unimod_sequences))
        for ptm in peptide_unimod_sequences:
            ptm = ptm.strip()
            peptide_unimod = re.findall(position_regex, ptm)
            if peptide_unimod:
                peptide_name = re.sub(position_regex, '', ptm)
                if len(peptide_unimod) > 1:
                    temp_ptm = ptm
                    peptide_position = []
                    for unimod_pos in peptide_unimod:
                        multiposition = re.search(unimod_pos, temp_ptm)
                        peptide_position.append(multiposition.start() - 1)
                        temp_ptm = re.sub("\("+multiposition.group()+"\)", '', temp_ptm, count=1)
                else:
                    peptide_position = [re.search(peptide_unimod[0], ptm).start() - 1]
                if peptide_name in peptide_sequences.keys():
                    peptide_sequences[peptide_name].update({ptm:peptide_position})
                else:
                    peptide_sequences[peptide_name] = {ptm:peptide_position}
        return peptide_sequences
    except EOFError:
        print("Unable to parse Input file") 
        return False

# Function for parsing peptide names from TSV file into a Python dictionary
def sequencePairing(fasta_file, tsv_file):
    try:
        protein_sequence = parseFASTA(fasta_file)
        peptide_sequence = parseTSV(tsv_file)
        if protein_sequence == False or peptide_sequence == False:
            raise Exception
        ppp_sequence = {}
        for protein_name, sequence in protein_sequence.items():
            for peptide_name, position in peptide_sequence.items():
                matching = re.search(peptide_name, sequence)
                if matching is not None:
                    for peptide_vSequences, peptide_vPositions in position.items():
                        protein_positions = []
                        for peptide_vPositions in peptide_vPositions:
                            protein_position = peptide_vPositions + matching.start()
                            protein_positions.append(protein_position)
                        protein_positions = ', '.join(str(str_pos) for str_pos in protein_positions)
                        if protein_name in ppp_sequence.keys():
                            ppp_sequence[protein_name].update({peptide_vSequences:protein_positions})
                        else:
                            ppp_sequence[protein_name] = {peptide_vSequences:protein_positions}
        return ppp_sequence
    except EOFError:
        print("Unable to pair protein and peptide sequences") 
        return False

app = FastAPI()

origins = [
    "https://ptm-finder.herokuapp.com/"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/uploadFiles/")
async def uploadFiles(fasta_upload: UploadFile = File(...), tsv_upload: UploadFile = File(...)):
    fasta_file = await fasta_upload.read() 
    tsv_file  = await tsv_upload.read() 
    data = sequencePairing(fasta_file, tsv_file)
    df = pd.DataFrame.from_dict({(i, j): (i, j, k) for i in data.keys() for j, k in data[i].items() }, orient='index')
    df.reset_index().drop(columns=['index'])
    json_package = df.to_json(index=False, orient='split')
    print(json_package)
    return {"Working":"OK"}