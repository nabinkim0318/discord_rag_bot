# # tests/test_query_planner_mixed.py
# # -*- coding: utf-8 -*-
# import pytest

# from rag_agent.query.query_planner import plan_query


# # A tiny helper to fetch first intent object by name
# def _find_intent(qp, name):
#     for it in qp.intents:
#         if it.intent == name:
#             return it
#     return None


# # Assert helpers
# def _assert_week(intent_obj, expected_week):
#     if expected_week is None:
#         # week is unspecified → either not present OR marked as needs_week
#         assert (
#             "week" not in intent_obj.extracted_info
#             or intent_obj.extracted_info.get("needs_week") is True
#         )
#     else:
#         assert intent_obj.extracted_info.get("week") == expected_week


# def _assert_audience(intent_obj, expected_aud):
#     if expected_aud is None:
#         # audience may default to "all" for resources; that's OK
#         pass
#     else:
#         assert intent_obj.extracted_info.get("audience") == expected_aud


# CASES = [
#     # 1
#     {
#         "q": "What's the Week 3 schedule, and share
#           the video resources for engineers.",
#         "expect": [
#             {"intent": "schedule", "week": 3, "aud": None},
#             {"intent": "resources", "week": None, "aud": "engineer"},
#         ],
#         "clarify": False,
#     },
#     # 2
#     {
#         "q": "When is the demo deadline and where are the slides for PMs?",
#         "expect": [
#             {"intent": "schedule", "week": None, "aud": None},
#             {"intent": "resources", "week": None, "aud": "pm"},
#         ],
#         "clarify": True,
#     },
#     # 3
#     {
#         "q": "Send me resources for wk5 and also confirm
#   whether the internship is paid.",
#         "expect": [
#             {"intent": "resources", "week": 5, "aud": None},
#             {"intent": "faq", "week": None, "aud": None},
#         ],
#         "clarify": False,
#     },
#     # 4
#     {
#         "q": "Is it eligible for CPT, and what happens in Week 1?",
#         "expect": [
#             {"intent": "faq", "week": None, "aud": None},
#             {"intent": "schedule", "week": 1, "aud": None},
#         ],
#         "clarify": False,
#     },
#     # 5
#     {
#         "q": "Share the RAG tutorials and the Week 4 pitch schedule.",
#         "expect": [
#             {"intent": "resources", "week": None, "aud": None},
#             {"intent": "schedule", "week": 4, "aud": None},
#         ],
#         "clarify": False,
#     },
#     # 6
#     {
#         "q": "I need the playlist for designers and the date of the matching.",
#         "expect": [
#             {"intent": "resources", "week": None, "aud": "designer"},
#             {"intent": "schedule", "week": None, "aud": None},
#         ],
#         "clarify": True,
#     },
#     # 7
#     {
#         "q": "When is the demo and do we have a training document?",
#         "expect": [
#             {"intent": "schedule", "week": None, "aud": None},
#             {"intent": "resources", "week": None, "aud": None},
#         ],
#         "clarify": True,
#     },
#     # 8
#     {
#         "q": "Where are the training videos, and what time are office hours
#   in Week 2?",
#         "expect": [
#             {"intent": "resources", "week": None, "aud": None},
#             {"intent": "schedule", "week": 2, "aud": None},
#         ],
#         "clarify": False,
#     },
#     # 9
#     {
#         "q": "Please send the form link and tell me if this is unpaid.",
#         "expect": [
#             {"intent": "resources", "week": None, "aud": None},
#             {"intent": "faq", "week": None, "aud": None},
#         ],
#         "clarify": False,
#     },
#     # 10
#     {
#         "q": "Week 5 schedule plus any additional materials for developers.",
#         "expect": [
#             {"intent": "schedule", "week": 5, "aud": None},
#             {"intent": "resources", "week": None, "aud": "engineer"},
#         ],
#         "clarify": False,
#     },
#     # 11
#     {
#         "q": "Is there an attendance policy, and what’s planned in W#6?",
#         "expect": [
#             {"intent": "faq", "week": None, "aud": None},
#             {"intent": "schedule", "week": 6, "aud": None},
#         ],
#         "clarify": False,
#     },
#     # 12
#     {
#         "q": "Slides for Week 7 and the date for team matching, please.",
#         "expect": [
#             {"intent": "resources", "week": 7, "aud": None},
#             {"intent": "schedule", "week": None, "aud": None},
#         ],
#         "clarify": True,
#     },
#     # 13
#     {
#         "q": "Share PM resources and the deadline this week.",
#         "expect": [
#             {"intent": "resources", "week": None, "aud": "pm"},
#             {"intent": "schedule", "week": None, "aud": None},
#         ],
#         "clarify": True,  # “this week” is ambiguous
#     },
#     # 14
#     {
#         "q": "Is it not paid? Also, where’s the Prompt Engineering lecture?",
#         "expect": [
#             {"intent": "faq", "week": None, "aud": None},
#             {"intent": "resources", "week": None, "aud": None},
#         ],
#         "clarify": False,
#     },
#     # 15
#     {
#         "q": "When is the pitch, and send tutorials for engineers in wk3.",
#         "expect": [
#             {"intent": "schedule", "week": None, "aud": None},
#             {"intent": "resources", "week": 3, "aud": "engineer"},
#         ],
#         "clarify": True,
#     },
#     # 16
#     {
#         "q": "Office hours in week 1 and RAG docs for designers.",
#         "expect": [
#             {"intent": "schedule", "week": 1, "aud": None},
#             {"intent": "resources", "week": None, "aud": "designer"},
#         ],
#         "clarify": False,
#     },
#     # 17
#     {
#         "q": "Give me all videos and tell me the Week 8 demo time.",
#         "expect": [
#             {"intent": "resources", "week": None, "aud": None},
#             {"intent": "schedule", "week": 8, "aud": None},
#         ],
#         "clarify": False,
#     },
#     # 18
#     {
#         "q": "Do we have unpaid participants, and any slides for PMs in Week 2?",
#         "expect": [
#             {"intent": "faq", "week": None, "aud": None},
#             {"intent": "resources", "week": 2, "aud": "pm"},
#         ],
#         "clarify": False,
#     },
#     # 19
#     {
#         "q": "What’s the schedule and the best course to watch first?",
#         "expect": [
#             {"intent": "schedule", "week": None, "aud": None},
#             {"intent": "resources", "week": None, "aud": None},
#         ],
#         "clarify": True,  # schedule lacks a week
#     },
#     # 20
#     {
#         "q": "Where’s the training form and when is matching for Week 4?",
#         "expect": [
#             {"intent": "resources", "week": None, "aud": None},
#             {"intent": "schedule", "week": 4, "aud": None},
#         ],
#         "clarify": False,
#     },
#     # 21
#     {
#         "q": "When is the Pitch Day, and do I have to attend it
# to be considered for team matching?",
#         "expect": [
#             {"intent": "schedule", "week": 4, "aud": None},
#             {"intent": "requirement", "week": None, "aud": "engineer"},
#         ],
#         "clarify": False,
#     },
#     # 22
#     {
#         "q": "Share the Week 2 tasks for designers and tell me what engineers
# should keep working on during that week.",
#         "expect": [
#             {"intent": "tasks", "week": 2, "aud": "designer"},
#             {"intent": "tasks", "week": 2, "aud": "engineer"},
#         ],
#         "clarify": False,
#     },
#     # 23
#     {
#         "q": "What exactly do I need to submit in Week 3 — is it only code, or
# do I also need a demo video and execution example?",
#         "expect": [{"intent": "submission", "week": 3, "aud": "engineer"}],
#         "clarify": False,
#     },
#     # 24
#     {
#         "q": "Do I need to complete both the Discord RAG Bot and the Job Tracker
# Agent assignments, or is choosing one enough?",
#         "expect": [{"intent": "requirement", "week": 1, "aud": "engineer"}],
#         "clarify": False,
#     },
#     # 25
#     {
#         "q": "If I miss the Week 3 submission deadline, will it affect my
# eligibility for Tier 1 certification or team matching?",
#         "expect": [
#             {"intent": "requirement", "week": 3, "aud": None},
#             {"intent": "certification", "week": None, "aud": None},
#         ],
#         "clarify": False,
#     },
#     # 26
#     {
#         "q": "When exactly do designers join teams, and how is that different
# from the week engineers join?",
#         "expect": [
#             {"intent": "schedule", "week": 2, "aud": "designer"},
#             {"intent": "schedule", "week": 4, "aud": "engineer"},
#         ],
#         "clarify": False,
#     },
#     # 27
#     {
#         "q": "What responsibilities does the lead engineer have compared to
# the project manager?",
#         "expect": [
#             {"intent": "roles", "week": None, "aud": "engineer"},
#             {"intent": "roles", "week": None, "aud": "pm"},
#         ],
#         "clarify": False,
#     },
#     # 28
#     {
#         "q": "Show me the checklist of onboarding steps I must complete in Week 1,
# and include the Discord setup instructions.",
#         "expect": [
#             {"intent": "checklist", "week": 1, "aud": None},
#             {"intent": "resources", "week": 1, "aud": "engineer"},
#         ],
#         "clarify": False,
#     },
#     # 29
#     {
#         "q": "What meetings count toward the 90% attendance requirement for
# Tier 1 certification — office hours or only team meetings?",
#         "expect": [{"intent": "certification", "week": None, "aud": None}],
#         "clarify": False,
#     },
#     # 30
#     {
#         "q": "Where can I post personal visa or CPT/OPT related questions if
# DMs to mentors are discouraged?",
#         "expect": [
#             {"intent": "communication", "week": None, "aud": "engineer"},
#             {"intent": "visa", "week": None, "aud": None},
#         ],
#         "clarify": False,
#     },
#     # 31
#     {
#         "q": "What are the specific Week 5–8 expectations for engineers after
# team matching, and should we use Agile sprints?",
#         "expect": [
#             {"intent": "tasks", "week": 5, "aud": "engineer"},
#             {"intent": "tasks", "week": 6, "aud": "engineer"},
#             {"intent": "tasks", "week": 7, "aud": "engineer"},
#             {"intent": "tasks", "week": 8, "aud": "engineer"},
#             {"intent": "requirement", "week": None, "aud": None},
#         ],
#         "clarify": False,
#     },
#     # 32
#     {
#         "q": "Do designers need to prepare high-fidelity designs before engineers
# join in Week 4, and where should they share them?",
#         "expect": [
#             {"intent": "tasks", "week": 3, "aud": "designer"},
#             {"intent": "communication", "week": None, "aud": "designer"},
#         ],
#         "clarify": False,
#     },
#     # 33
#     {
#         "q": "When exactly is Demo Week, and what deliverables are expected
# from the team before presenting?",
#         "expect": [
#             {"intent": "schedule", "week": 11, "aud": None},
#             {"intent": "submission", "week": 10, "aud": "team"},
#         ],
#         "clarify": False,
#     },
#     # 34
#     {
#         "q": "Can you show me the checklist of what must be included in the
# final prototype demo?",
#         "expect": [{"intent": "checklist", "week": 11, "aud": "team"}],
#         "clarify": False,
#     },
#     # 35
#     {
#         "q": "Who creates the main GitHub repository, and what should the lead
# engineer configure for branching and reviews?",
#         "expect": [
#             {"intent": "roles", "week": None, "aud": "pm"},
#             {"intent": "roles", "week": None, "aud": "engineer"},
#         ],
#         "clarify": False,
#     },
#     # 36
#     {
#         "q": "Is missing an office hour counted as missing a required meeting
# for certification purposes?",
#         "expect": [
#             {"intent": "certification", "week": None, "aud": None},
#             {"intent": "schedule", "week": None, "aud": None},
#         ],
#         "clarify": False,
#     },
#     # 37
#     {
#         "q": "What costs are covered by the Bootcamp — are API calls, cloud
# hosting, and local GPU expenses all included?",
#         "expect": [{"intent": "resources", "week": None, "aud": None}],
#         "clarify": False,
#     },
#     # 38
#     {
#         "q": "Is there a maximum allowed delay for CPT approval before I get
# moved to another cohort?",
#         "expect": [{"intent": "visa", "week": None, "aud": None}],
#         "clarify": False,
#     },
#     # 39
#     {
#         "q": "Where do I find the submission form link for Week 3, and what
# fields must I fill out?",
#         "expect": [
#             {"intent": "submission", "week": 3, "aud": "engineer"},
#             {"intent": "resources", "week": 3, "aud": None},
#         ],
#         "clarify": False,
#     },
#     # 40
#     {
#         "q": "For Tier 2 and Tier 3 certifications, what benefits are included
# beyond just the badge?",
#         "expect": [{"intent": "certification", "week": None, "aud": None}],
#         "clarify": False,
#     },
#     # 41
#     {
#         "q": "What is the Week 1 schedule for designers?",
#         "expect": [{"intent": "schedule", "week": 1, "aud": "designer"}],
#         "clarify": False,
#     },
#     # 42
#     {
#         "q": "When do engineers need to submit their Week 3 assignment?",
#         "expect": [{"intent": "submission", "week": 3, "aud": "engineer"}],
#         "clarify": False,
#     },
#     # 43
#     {
#         "q": "What tasks are assigned to engineers in Week 2?",
#         "expect": [{"intent": "tasks", "week": 2, "aud": "engineer"}],
#         "clarify": False,
#     },
#     # 44
#     {
#         "q": "Where should I post my self-introduction during onboarding?",
#         "expect": [{"intent": "communication", "week": 1, "aud": None}],
#         "clarify": False,
#     },
#     # 45
#     {
#         "q": "What responsibilities does a lead engineer have?",
#         "expect": [{"intent": "roles", "week": None, "aud": "engineer"}],
#         "clarify": False,
#     },
#     # 46
#     {
#         "q": "What is required to earn Tier 1 certification?",
#         "expect": [{"intent": "certification", "week": None, "aud": None}],
#         "clarify": False,
#     },
#     # 47
#     {
#         "q": "When do designers get matched to teams?",
#         "expect": [{"intent": "schedule", "week": 2, "aud": "designer"}],
#         "clarify": False,
#     },
#     # 48
#     {
#         "q": "Which channel is used for tech stack sharing?",
#         "expect": [{"intent": "communication", "week": 1, "aud": None}],
#         "clarify": False,
#     },
#     # 49
#     {
#         "q": "What are the required deliverables for the final group demo?",
#         "expect": [{"intent": "submission", "week": 11, "aud": None}],
#         "clarify": False,
#     },
#     # 50
#     {
#         "q": "Which resources are provided for engineer training?",
#         "expect": [{"intent": "resources", "week": None, "aud": "engineer"}],
#         "clarify": False,
#     },
# ]


# @pytest.mark.parametrize("case", CASES, ids=[str(i + 1) for i in range(len(CASES))])
# def test_mixed_intents(case):
#     q = case["q"]
#     expected = case["expect"]
#     expect_clarify = case["clarify"]

#     qp = plan_query(q)

#     # clarity expectation
#     assert (
#         qp.requires_clarification is expect_clarify
#     ), f"Clarification mismatch for: {q}. Got: {qp.requires_clarification}"

#     # verify each expected intent exists, and check extracted fields
#     for exp in expected:
#         intent_name = exp["intent"]
#         it = _find_intent(qp, intent_name)
#         assert (
#             it is not None
#         ), f"Missing intent '{intent_name}' for: {q}. Got:
# {[i.intent for i in qp.intents]}"

#         # Week checks (None means unspecified is OK)
#         _assert_week(it, exp.get("week"))

#         # Audience checks (only meaningful for resources)
#         if intent_name == "resources":
#             _assert_audience(it, exp.get("aud"))
