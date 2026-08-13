from babbly.adapters.azazel import AzazelAdapter
from babbly.core.engine import SituationEngine


def main():
    adapter = AzazelAdapter(lambda: {"system": "azazel", "state": "unknown"})
    snapshot = SituationEngine([adapter]).collect()
    print(snapshot.to_dict())


if __name__ == "__main__":
    main()
