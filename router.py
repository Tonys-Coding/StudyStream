def route_query(query: str):

    q = query.lower()

    routes = []

    if any(word in q for word in [
        "what",
        "why",
        "how",
        "explain",
        "define"
    ]):
        routes.append("faq")

    if any(word in q for word in [
        "quiz",
        "practice",
        "test"
    ]):
        routes.append("quiz")

    if any(word in q for word in [
        "study",
        "plan",
        "schedule",
        "prepare",
        "review"
    ]):
        routes.append("study")

    if not routes:
        routes.append("faq")

    return routes
