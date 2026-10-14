"""Twelve synthetic, bounded proof-test cases and independent policy oracle.

These scenarios exercise code under stipulated inputs, not laboratory truth,
customer outcomes, or a blinded evaluation against human expertise.
"""
from __future__ import annotations

import itertools
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from proof_hinge_research import evaluate  # noqa: E402

# id, domain, qualified payoff, unqualified payoff, deferral cost, controlled
# test cost, scenario mode; utility units are arbitrary and entirely fictional.
SPECS = (
    ('Q01', 'neutral_atom', 90, -230, -30, 9, 'standard'),
    ('Q02', 'neutral_atom', 100, -200, -20, 3, 'ambiguous_only'),
    ('Q03', 'neutral_atom', 80, -260, -40, 18, 'three_worlds'),
    ('Q04', 'neutral_atom', 20, -80, -10, 200, 'excessive_cost'),
    ('M01', 'critical_materials', 100, -320, -60, 17, 'standard'),
    ('M02', 'critical_materials', 60, -280, -35, 12, 'two_tests'),
    ('M03', 'critical_materials', 120, -420, -50, 8, 'sensitive'),
    ('M04', 'critical_materials', 100, -240, -25, 6, 'standard'),
    ('C01', 'ai_cyber_assurance', 100, -500, -70, 10, 'standard'),
    ('C02', 'ai_cyber_assurance', 140, -300, -50, 14, 'ambiguous_only'),
    ('C03', 'ai_cyber_assurance', 90, -260, -40, 14, 'stable'),
    ('C04', 'ai_cyber_assurance', 70, -160, -45, 11, 'three_worlds'),
)


def make_case(spec):
    ident, domain, good, bad, delay, price, mode = spec
    worlds = ['qualified', 'unqualified']
    if mode == 'three_worlds':
        worlds.append('uncharacterized')
    actions = {
        'commit': {'qualified': good, 'unqualified': bad},
        'defer': {'qualified': delay, 'unqualified': 0},
    }
    if len(worlds) == 3:
        actions['commit']['uncharacterized'] = -100
        actions['defer']['uncharacterized'] = 0

    def test(name, cost, mapping):
        return {'name': name, 'assumed_cost': cost, 'possible_outcomes_by_world': mapping}

    # Low-cost narrative repetition cannot distinguish any hypothetical world.
    choices = [test('Narrative summary', 1, {w: ['repeat'] for w in worlds})]
    if mode != 'ambiguous_only':
        choices.append(test('Controlled assessment', price, {w: [w] for w in worlds}))
    choices.append(test('Inconclusive assessment', 2, {w: [w, 'unclear'] for w in worlds}))
    if mode == 'two_tests':
        choices.append(test('Second controlled assessment', 25, {w: ['second_' + w] for w in worlds}))

    result = {
        'case_id': ident,
        'claim': f'Synthetic {domain} scenario {ident}',
        'source': {'kind': 'wholly_synthetic_test_fixture', 'locator': f'{ident} artificial data'},
        'worlds': worlds, 'actions': actions, 'tests': choices,
    }
    if mode == 'sensitive':
        result['payoff_variants'] = [{'name': 'all outcomes equally neutral',
                                      'actions': {a: {w: 0 for w in worlds} for a in actions}}]
    elif mode == 'stable':
        result['payoff_variants'] = [{'name': 'same stipulated payoffs',
                                      'actions': {a: dict(v) for a, v in actions.items()}}]
    return result


def exhaustive_policy_oracle(case):
    """Enumerate every observation-to-action policy, independently of engine."""
    payoffs = case['actions']
    best = {w: max(row[w] for row in payoffs.values()) for w in case['worlds']}
    regret = {(a, w): best[w] - row[w] for a, row in payoffs.items() for w in case['worlds']}
    baseline = min(max(regret[a, w] for w in case['worlds']) for a in payoffs)
    nets = {}
    for candidate in case['tests']:
        outcome_sets = candidate['possible_outcomes_by_world']
        labels = sorted(set(label for values in outcome_sets.values() for label in values))
        worst = min(
            max(regret[policy[labels.index(label)], world]
                for world in case['worlds'] for label in outcome_sets[world])
            for policy in itertools.product(payoffs, repeat=len(labels))
        )
        nets[candidate['name']] = baseline - worst - candidate['assumed_cost']
    return baseline, nets


class SyntheticBenchmarkTests(unittest.TestCase):
    def test_bounded_matrix_and_provenance(self):
        self.assertEqual(len(SPECS), 12)
        self.assertEqual(len({row[0] for row in SPECS}), 12)
        for domain in ('neutral_atom', 'critical_materials', 'ai_cyber_assurance'):
            self.assertEqual(sum(s[1] == domain for s in SPECS), 4)
        for spec in SPECS:
            self.assertEqual(make_case(spec)['source']['kind'], 'wholly_synthetic_test_fixture')

    def test_predeclared_abstentions(self):
        statuses = {s[0]: evaluate(make_case(s))['research_status'] for s in SPECS}
        for ident in ('Q02', 'Q04', 'C02'):
            self.assertEqual(statuses[ident], 'ABSTAIN_NO_POSITIVE_PROOF_TEST')
        self.assertEqual(statuses['M03'], 'ABSTAIN_ASSUMPTION_SENSITIVE')
        self.assertEqual(sum(s.startswith('ABSTAIN') for s in statuses.values()), 4)

    def test_cheapest_first_is_only_a_synthetic_comparator(self):
        wins = 0
        for spec in SPECS:
            case = make_case(spec)
            result = evaluate(case)
            lowest_cost = min(case['tests'], key=lambda t: (t['assumed_cost'], t['name']))
            if result['research_status'] == 'REQUEST_EVIDENCE_FOR_REVIEW':
                nets = {t['name']: t['net_modeled_regret_reduction'] for t in result['test_ranking']}
                self.assertGreater(nets[result['priority_test_if_assumptions_hold']], nets[lowest_cost['name']])
                wins += 1
        self.assertEqual(wins, 8)

    def test_no_claim_or_action_promotion(self):
        for spec in SPECS:
            result = evaluate(make_case(spec))
            self.assertIs(result['claims_verified'], False)
            self.assertIs(result['independent_validation'], False)
            self.assertEqual(result['decision_authority'], 'NONE')
            self.assertIs(result['repo_write_performed'], False)


def one_case_test(spec):
    def test(self):
        case = make_case(spec)
        result = evaluate(case)
        baseline, nets = exhaustive_policy_oracle(case)
        self.assertAlmostEqual(baseline, result['baseline']['worst_regret'])
        self.assertEqual([t['name'] for t in result['test_ranking']],
                         sorted(nets, key=lambda n: (-nets[n], n)))
        for row in result['test_ranking']:
            self.assertAlmostEqual(row['net_modeled_regret_reduction'], nets[row['name']])
            self.assertFalse(row['outcome_assumptions_verified'])
    return test


for row in SPECS:
    setattr(SyntheticBenchmarkTests, 'test_case_' + row[0].lower(), one_case_test(row))

if __name__ == '__main__':
    unittest.main()
