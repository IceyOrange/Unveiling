import sys
from dotenv import load_dotenv

load_dotenv()

from crew import SpatioTemporalCrew


def run():
    if len(sys.argv) < 2:
        print("Usage: python main.py <topic>")
        print('Example: python main.py "AI"')
        print('Example: python main.py "短视频的兴起"')
        sys.exit(1)

    topic = sys.argv[1]

    print(f"\n{'='*60}")
    print(f"  Spatio-Temporal Analogy Analysis")
    print(f"  Topic: {topic}")
    print(f"{'='*60}\n")

    crew_instance = SpatioTemporalCrew()
    result = crew_instance.crew().kickoff(inputs={"topic": topic})

    print(f"\n{'='*60}")
    print(f"  Analysis Complete")
    print(f"{'='*60}\n")
    print(result)


if __name__ == "__main__":
    run()
