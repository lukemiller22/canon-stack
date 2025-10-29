- # Theological Text Metadata Annotation Prompt
    - You are helping to create high-quality metadata for theological text chunks to improve RAG (Retrieval Augmented Generation) performance. Your task is to analyze text chunks and provide structured metadata following specific guidelines.
- ## Text Chunking Context
    - Chunks are approximately 1000-1500 characters
    - Generally follow paragraph boundaries unless paragraphs exceed 1500 characters
- ## Metadata Structure
    - For each chunk, provide metadata in this exact format:
    - ```plain text
      * Topics: [[Topic1]], [[Topic2]], [[Topic3]]
      * Concepts:: [[Concept1]], [[Concept2]]
      * Themes:: [[Theme1]], [[Theme2]]
      * Function::
         * [[Category/Element]] Description or quote
         * [[Category/Element]] Description or quote
      * Scripture-References: [Bible references if any]
      * Proper-Nouns:: [[Name1]], [[Name2]], [[Place1]]
      ```
- ## Critical Constraints
    - ### Topics Index (90% Fixed)
        - Index is organized like this: Domain > Subject > Topic
        - Use ONLY topics from the provided Topics Index
        - **Exception**: You may add NEW topics ONLY under these three categories, and ONLY after checking that existing topics don't fit:
            - "History & Biography > Historical Groups"
            - "History & Biography > Historical Individuals"
            - "Christian Life > Virtues & Vices"
        - Choose 2-4 most relevant topics per chunk
        - Use the most specific level that accurately describes the chunk's content: Topic when the content focuses on a specific area (e.g., [[Topic/War]]), Subject when it addresses a broader category without focusing on specifics (e.g., [[Subject/Family]]), or Domain only when discussing the entire field broadly (e.g., [[Domain/History & Biography]]). Do not include higher levels automatically—each level should only be tagged if the content actually engages at that level of specificity.
        - Use [[Index: Topics]]
    - ### Concepts Index (Completely Fixed)
        - Use ONLY concepts from the provided Concepts Index (based on Adler's Syntopicon)
        - **NO additions allowed** - this is a closed list of 102 universal concepts
        - Better to leave blank than force an inappropriate concept
        - Usually 1-3 concepts per chunk
        - Use [[Index: Concepts]]
    - ### Function Elements (Completely Fixed)
        - Use ONLY elements from the provided Function framework (113 elements across 8 categories)
        - **NO additions allowed** - use namespaced format: `Category/Element`
        - **Required**: Every chunk must have at least one function element. Typically 3-5 function elements per chunk.
        - Categories: Semantic, Logical, Narrative, Personal, Practical, Symbolic, Reference, Structural
        - Use [[Index: Function]]
    - ### Themes (Flexible)
        - Identify semantic meaning, especially for figurative language, stories, poetry
        - Use descriptive phrases that capture the deeper meaning
        - Can create new themes as needed
    - ### Scripture-References (Completely Fixed)
        - Only add tags if a verse, chapter, or book of the Scriptures (66 books) is mentioned.
        - Normalize: Jn. 3, John 3, and third chapter of John's gospel all become "John 3"
        - Expand: If John 3:16 is mentioned, tag both "John 3" and "John 3:16".
        - For example:
            - Input: "Jn. 3:16"
            - Output: `[[John 3]]`, `[[John 3:16]]`
    - ### Proper-Nouns (Flexible)
        - May include People, Places, Groups, Ideologies, Events, etc.
- ## Quality Guidelines
    1. **Accuracy**: Only use items from the provided indexes unless they are "Flexible"
    2. **Relevance**: Choose the most fitting tags, don't force inappropriate fits. When in doubt about tags, choose the closest available option or leave blank rather than creating new tags for fixed lists.
    3. **Completeness**: Every chunk needs function elements, topics, and concepts. Most will need themes and have proper-nouns. Some will have scripture-references.
    4. **Precision**: Be specific in element descriptions for the function tags
    5. **Consistency**: Use the same approach across similar content types
- ## Example Function Elements with Namespaces
    - [[Logical/Claim]] The author asserts that...
    - [[Semantic/Example]] Illustration of reading Plato vs. commentary
    - [[Symbolic/Metaphor]] "Clean sea breeze of the centuries"
    - [[Personal/Experience]] Lewis recalls his first encounter with...
    - [[Practical/Principle]] After reading a new book, read an old one
    - [[Reference/Commentary]] Explanation of the Athanasian Creed
    - Remember: When in doubt about categories, choose the closest available option or leave blank rather than creating new terms. The goal is consistent, high-quality metadata that will significantly improve retrieval over pure vector search.
