from rag_agent.query.query_planner import plan_query

print(
    plan_query("What is the Week 3 schedule and the ", "video resources for engineers?")
)
print()
print(plan_query("resources for wk5 for PMs"))

# print(plan_query("What is the Week 3 schedule and
# the video resources for engineers?"))
# print(plan_query("Is the internship paid and what's the OPT/CPT policy?"))
# print(plan_query("When is the demo deadline? Also send the form link."))
# print(plan_query("resources for wk5 for PMs"))
