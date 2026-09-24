from app.agent.router import route_query_intent


def test_rag_routing():
    assert route_query_intent('EXPLAIN WHAT THIS PDF CONTAINED', has_document_context=True) == 'rag'
    assert route_query_intent('EXPLAIN ABOUT THIS PDF', has_document_context=True) == 'rag'
    assert route_query_intent('explain the attached files.', has_document_context=True) == 'rag'
    assert route_query_intent('what is in this document', has_document_context=False) == 'rag'
    assert route_query_intent('summarize the uploaded resume', has_document_context=False) == 'rag'
    assert route_query_intent('Who is Saurabh according to the document?', has_document_context=True) == 'rag'
    assert route_query_intent('Where did he study according to his resume?', has_document_context=True) == 'rag'
    assert route_query_intent('create a word doc of 10 students', has_document_context=False) == 'document'
    assert route_query_intent('generate a pdf report', has_document_context=False) == 'document'
    assert route_query_intent('make an excel spreadsheet', has_document_context=False) == 'document'
    assert route_query_intent('run python script to calculate primes', has_document_context=False) == 'coding'
    assert route_query_intent('hello how are you', has_document_context=False) == 'chat'
    # Critical: Greetings and general chat MUST be 'chat' even if has_document_context is True
    assert route_query_intent('hi', has_document_context=True) == 'chat'
    assert route_query_intent('hello', has_document_context=True) == 'chat'
    assert route_query_intent('can you calculate 25 * 40?', has_document_context=True) == 'chat'
    assert route_query_intent('write a python script to sort a list', has_document_context=True) == 'coding'
    assert route_query_intent('create an excel spreadsheet of sales', has_document_context=True) == 'document'

