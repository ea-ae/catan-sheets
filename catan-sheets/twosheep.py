import json
from google.cloud import firestore as fs
from google.cloud.firestore import Client
from google.cloud.firestore_bundle import FirestoreBundle



def main():
    db = fs.Client(project="twosheep-b6b02")

    # Reference the document
    doc_ref = db.document("replays/-OFYM-JbR3OXfu0XAdp_")

    doc = doc_ref.get()
    print(doc)

    # with open("payload.2sr", mode="rb") as f:
    #     ...


if __name__ == '__main__':
    main()

