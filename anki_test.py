# 
# anki_test.py - Tarah Z. Tamayo
#    -- Testing out retrieval and creation of collections / decks / cards using the anki library
# 

import os
from zipfile import ZipFile
import anki
import json

cwd = os.getcwd()
testfile = cwd + "/data/test.apkg"
tmpdir = cwd + "/data/tmp/"
with ZipFile(testfile, "r") as z:
    z.extractall(tmpdir)

print("\nCOLLECTION")
fname = tmpdir + "collection.anki2"
colln = anki.Collection(fname)
print(colln)

print("\nDECKS")
decks = colln.decks.all_names_and_ids()
deck = colln.decks.get(decks[1].id)
print(deck)

print("\nCARDS")
cards = colln.decks.cids(deck['id'])
card = colln.getCard(cards[0])
print(card)
print("\/\/\/\/ NOTE \/\/\/\/")
note = colln.getNote(card.nid)
print(note)

print("\nMODELS")
for model in colln.models.all():
    print(model)
    print()

print("\nCREATING A COLLECTION...")
new_testfile = cwd + "/data/test/collection.anki2"
new_colln = anki.Collection(new_testfile)
print(new_colln)

print("\nCREATING A DECK...")
deck = new_colln.decks.id("Test 1::Test 2::Test 3")
print(new_colln.decks.all_names_and_ids())

print("\nGET MODELS")
models = new_colln.models.all()
# For what I'm doing I'll only want to be using default models "Basic" and "Basic (and reversed card)" - these are built in
# and easy to retrieve
for m in models:
    print(m)
    print()
    # We want the Basic & Reversed model
    if m['name'] == "Basic (and reversed card)":
        model = m

print("\nCREATING A BASIC NOTE...")
# Looking at collection.py, this creates a new note with the active model
# note = new_colln.newNote()
# Let's choose a model with
note = anki.notes.Note(new_colln, model)
note.fields = ['to go', 'gehen']
print(note)

print("\nADDING NOTE TO DECK...")
new_colln.add_note(note, deck)

print("\nWRITING THE COLLECTION...")
new_colln.close()

print("\nREADING THE COLLECTION...")
new_colln = anki.Collection(new_testfile)
print(new_colln)

print("\nREADING ALL NOTES...")
all_notes = new_colln.find_notes("")
for n in all_notes:
    print(new_colln.getNote(n))
    print()