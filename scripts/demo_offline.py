#!/usr/bin/env python3
"""A safe, fully offline, SYNTHETIC FLIN learning and routing tutorial.

No Wikipedia/API/Ollama call; no real research evidence is claimed. Uses a
throwaway temporary SQLite database that is deleted at program exit.
"""
from __future__ import annotations
import os
import sys
import tempfile
from pathlib import Path


if __name__ == '__main__':
    # Keep real user data completely untouched; also force headless Matplotlib.
    sys.argv = [sys.argv[0], '--cpu-info']
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    with tempfile.TemporaryDirectory(prefix='flin-offline-demo-') as temp:
        os.environ['BRAIN_DATA_DIR'] = temp
        import flin_desktop as flin

        explanations = {
            'Fourier transform': 'The Fourier transform is a mathematical transformation used to analyze frequency content.',
            'Laplace transform': 'The Laplace transform is a mathematical integral transformation used in system analysis.',
            'Eigenvalue': 'An eigenvalue is a scalar associated with a linear transformation and an eigenvector.',
        }

        def event(*labels):
            return [{'label': label, 'explanation': explanations[label],
                     'position': float(i), 'url': ''}
                    for i, label in enumerate(labels)]

        with flin.database(path=Path(temp) / 'synthetic_demo.sqlite3') as db:
            flin.abc_enable(db)
            for index, labels in enumerate((
                    ('Fourier transform', 'Eigenvalue'),
                    ('Fourier transform', 'Laplace transform'),
                    ('Fourier transform', 'Eigenvalue')),
                    start=1):
                outcome = flin.abc_ingest_cluster(
                    db, event(*labels), f'synthetic-input-{index}',
                    gate_label='SYNTHETIC_EDUCATIONAL_EXAMPLE')
                print(f'Input event #{index}: {" -> ".join(labels)}; {outcome}')
            print('\nLearned directed routing preferences (NOT mathematical implications):')
            for left, right, weight, observations in db.execute('''
                SELECT a.label,b.label,e.weight,e.observations FROM abc_edges e
                JOIN abc_units a ON e.src=a.id JOIN abc_units b ON e.dst=b.id
                ORDER BY weight DESC'''):
                print(f'  {left} -> {right}: weight={weight:.3f}, observed={observations}')
            outcome = flin.abc_simulate(db, 'Fourier transform', pulse_hz=50,
                                        input_duration=1.0, save=False, random_seed=42)
            print('\nSimulation: 50 pulses, one directed exit per step (fixed RNG seed).')
            print('Emitted pulses:', outcome['input_pulses'])
            print('Activated memories:', outcome['activated_count'])
            print('Response distribution:')
            for item in outcome.get('distribution', [])[:10]:
                print(f'  {item["label"]}: proportion={item["proportion"]:.3f}')
            print('\nTemporary dataset deleted when this demonstration exits.')
            print('No inference, theorem validation, or external research was performed.')
