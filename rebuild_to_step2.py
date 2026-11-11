#!/usr/bin/env python3
"""Offline rebuild raw dataset -> STEP 1 -> STEP 2, then refresh handoff.
Python >= 3.10, stdlib only. No answer labels, API, inference, Docker/GPU.
"""
from pathlib import Path
import subprocess,sys,shutil

ROOT=Path(__file__).resolve().parent
ST1=ROOT/'01_PREPROCESSING'
ST2=ROOT/'02_QUESTION_CONVERTER'
RAW=ROOT/'00_RAW_INPUT'/'train_biz101_no_labels.zip'
HAN=ROOT/'HANDOFF_AFTER_STEP2'

def run(cwd,*args):
    print('RUN',cwd.name, *args,flush=True)
    subprocess.run([sys.executable,*map(str,args)],cwd=cwd,check=True)

def cp(source,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)

def main():
    if not RAW.is_file(): raise SystemExit('Missing raw mini archive: '+str(RAW))
    prior_readme=(ST1/'README.md').read_bytes()
    run(ST1,'analyze_step1.py',str(RAW))
    run(ST1,'finalize_step1.py')
    (ST1/'README.md').write_bytes(prior_readme)
    (ST1/'STEP1_REPORT.md').unlink(missing_ok=True) # historical full-train text
    run(ST2,'build_step2.py','--step1',str(ST1),'--out',str(ST2))
    run(ST2,'verify_step2.py','--step1',str(ST1),'--out',str(ST2))
    # Keep separate raw layer outputs and ready-to-receive handoff in sync
    mapping={
        '01_PREPROCESSING/schema.json':'schema.json',
        '01_PREPROCESSING/business_rules.json':'business_rules.json',
        '01_PREPROCESSING/data_dictionary.md':'data_dictionary.md',
        '01_PREPROCESSING/biz_101.sqlite':'database/biz_101.sqlite',
        '02_QUESTION_CONVERTER/converted_questions.jsonl':'converted_questions.jsonl',
        '02_QUESTION_CONVERTER/converted_question.schema.json':'converted_question.schema.json'
    }
    for a,b in mapping.items(): cp(ROOT/a,HAN/b)
    run(ROOT,'verify_package.py')
    print('PASS: STEP 1 -> STEP 2. Handoff ready with 10 converted questions.')

if __name__=='__main__':main()
