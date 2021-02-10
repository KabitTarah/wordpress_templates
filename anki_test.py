import os
from zipfile import ZipFile
import anki

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