from transformers import BertForSequenceClassification, BertTokenizer
import torch
from joblib import load


model = BertForSequenceClassification.from_pretrained('boapps/kmdb_classification_model')
tokenizer = BertTokenizer.from_pretrained('SZTAKI-HLT/hubert-base-cc')

print('loaded model')

model.eval()
with torch.no_grad():
    inputs = tokenizer(""""A Debreceni Regionális Nyomozó Ügyészség három korrupt rendőrrel és egy vállalkozóval szemben emelt vádat, amiért leseftelték, hogy a vállalkozót ne büntessék meg, miközben szabálytalanul szállít szalmabálákat.

A vádirat szerint 2021 márciusában egy Hajdú-Bihar vármegyei mezőgazdasági vállalkozó azzal kereste meg a szabálysértési referensként dolgozó rendőr ismerősét, hogy tehergépkocsival a közlekedési szabályok megsértésével, – a gépjármű leengedett oldalfalai mellett – 150 darab körbálát kíván közúton a tanyájára szállítani.

A férfi azt kérte a rendőrtől, hogy segítsen neki abban, hogy amíg szabálytalanul szállítja a bálákat, járművét ne vonják közúti ellenőrzés alá és ne büntessék meg.

A megkeresett rendőr erre ígéretet tett, és cserébe jogtalan előnyként azt kérte, hogy a férfi biztosítsa számára az egyik tehergépkocsi használatát, amivel tíz köbméter földet kíván fuvarozni. A vállalkozó beleegyezett az alkuba, és másnap oda is adta a tehergépkocsit a rendőrnek.

A rendőr a bálaszállítás előtt felhívta az aznap közterületi járőrszolgálatot ellátó kollégáit, akiket megkért arra, hogy a nagy mennyiségű szalmabálát szállító járművet ne vonják ellenőrzés alá. Ezután ismerősét arról biztosította, hogy a szállítást megkezdhetik, mivel a kollégáival megbeszélte, hogy az ügyben nem lesz rendőri intézkedés.

A nyomozó ügyészség minősített hivatali vesztegetés elfogadásának bűntettével vádolja a rendőrt, és végrehajtandó szabadságvesztés büntetés kiszabását indítványozta vele szemben. A vállalkozó esetében – aki minősített hivatali vesztegetés bűntettét követte el – felfüggesztett szabadságvesztés büntetés kiszabására tett indítványt, továbbá mindkettőjük esetében pénzbüntetés kiszabását is kérte. A hivatali visszaélés bűntettét elkövető járőrökkel szemben pénzbüntetés és katonai mellékbüntetés a vádiratban indítványozott büntetés.""", return_tensors="pt", padding=True, truncation=True, max_length=512)
    output = model(**inputs, output_hidden_states=True)
    cls_embedding = output.hidden_states[-1][:, 0, :].squeeze().numpy()

    svm_classifier = load('svm_classifier_category.joblib')
    pred = svm_classifier.predict([cls_embedding])
    print(pred)
