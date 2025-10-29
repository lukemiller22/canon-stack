## Setup Instructions

### Quick Setup
```bash
# Run the setup script
./setup.sh

# Activate virtual environment
source venv/bin/activate

# Check pipeline status
python pipeline_manager.py --stage status
```

### Manual Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create processing directories
mkdir -p theological_processing/{01_sources,02_chunked,03_annotated,04_complete,05_deployed,metadata,logs,templates,rejected}
```

## Theological Text Metadata Annotation Prompt
    - You are helping to create high-quality metadata for theological text chunks to improve RAG (Retrieval Augmented Generation) performance. Your task is to analyze text chunks and provide structured metadata following specific guidelines.
## Text Chunking Context
    - Chunks are approximately 1000-1500 characters
    - Generally follow paragraph boundaries unless paragraphs exceed 1500 characters
    - **Identify chunks for annotation by locating the `Chunk::` label in the markdown file**
    - Each `Chunk::` entry represents one text segment that requires complete metadata annotation
## Metadata Structure
    - For each chunk, provide metadata in this exact format:
    - ```plain text
      * concepts:: [[Concept1]], [[Concept2]]
      * topics:: [[Concept1/Topic1]], [[Concept2/Topic2]]
      * terms:: [[Term1]], [[Term2]]
      * discourse-elements::
         * [[Category/Element]] Description or quote
         * [[Category/Element]] Description or quote
      * scripture-references:: [Bible references if any, standardized format]
      * structure-path:: Breadcrumb format (e.g. [[Section > Subsection 1 > Subsection 2]])
      * named-entities:: [[Person/Entity]], [[Place/Entity]], [[Event/Entity]], [[Ideology/Entity]], [[Period/Entity]], [[Work/Entity]], [[Group/Entity]]
      ```
## Critical Constraints
    - ### Concepts Index (Fixed)
        - Use ONLY concepts from the provided Concepts Index (inspired by Adler's Syntopicon)
        - **NO additions allowed** - this is a closed list of perennial, fundamental concepts
        - Better to leave blank than force an inappropriate concept
        - Usually 1-3 concepts per chunk
        - Use [[I: Concepts]]
    - ### Topics Index (Flexible)
        - When assigning topics under selected concepts, follow Mortimer Adler's syntopical methodology by focusing on **questions, issues, aspects, or debates** rather than simple subtopics or themes. Each topic should represent a significant theological discussion point that could span multiple authors, traditions, or time periods.
        - Topics must use the namespaced format `[[Concept/Topic]]` to enable efficient checking against existing topic lists. Before creating a new topic, review the existing topic list for your assigned concept(s) to determine if the content fits an established category.
        - What Makes a Good Topic?
            - **Focus on Questions and Debates:** Topics should capture the major questions theologians ask about this concept. For example:
                - Under "Authority": `[[Authority/Scripture vs Tradition]]`, `[[Authority/Papal Infallibility]]`, `[[Authority/Individual Conscience vs Church Teaching]]`
                - Under "Salvation": `[[Salvation/Faith vs Works]]`, `[[Salvation/Universal vs Particular]]`, `[[Salvation/Assurance and Perseverance]]`
            - **Emphasize Issues and Aspects:** Identify the key facets of theological discussion around the concept:
                - Under "Prayer": `[[Prayer/Intercessory Prayer]]`, `[[Prayer/Contemplative vs Petitionary]]`, `[[Prayer/Corporate vs Private]]`
                - Under "Scripture": `[[Scripture/Inspiration and Inerrancy]]`, `[[Scripture/Canon Formation]]`, `[[Scripture/Interpretation Methods]]`
            - **Capture Cross-Traditional Debates:** Topics should be broad enough to encompass how different theological traditions approach the same fundamental questions, allowing for syntopical comparison across authors and eras.
        - Before creating a new topic, check if the content could reasonably fit under an existing topic for that concept. Create new topics only when the content addresses a genuinely distinct question, issue, or debate that existing topics do not adequately cover.
        - Use [[I: Topics]]
    - ### Term Index (Flexible)
        - When selecting terms for the inventory, follow Mortimer Adler's methodology for creating a comprehensive vocabulary that captures how readers actually search for and think about theological concepts. Terms should function as entry points that connect users to relevant content through the language they naturally use.
        - What Makes a Good Term?
            - **Synonyms and Variant Expressions:** Include alternative ways the same concept is expressed across different traditions, time periods, and levels of formality:
                - For content about salvation: "justification," "being made right with God," "declared righteous," "forensic righteousness"
                - For content about Scripture: "Word of God," "Holy Writ," "Sacred Text," "divine revelation"
            - **Familiar and Colloquial Expressions:** Capture how ordinary believers and popular theological discourse refer to concepts:
                - For content about sin: "fallen nature," "total depravity," "original sin," "corruption," "the flesh"
                - For content about sanctification: "growing in grace," "spiritual maturity," "becoming like Christ"
            - **Poetic and Literary Language:** Include metaphorical and symbolic language that appears in theological literature:
                - For content about redemption: "purchased by blood," "ransomed," "bought back," "delivered from bondage"
                - For content about the church: "bride of Christ," "body of believers," "pilgrim people"
            - **Technical and Scholarly Terms:** Include precise theological vocabulary that specialists use:
                - For content about Christology: "hypostatic union," "communicatio idiomatum," "anhypostatic"
                - For content about Trinity: "perichoresis," "economic Trinity," "immanent Trinity"
            - **Memorable Phrases:** Look for distinctive expressions that function as conceptual shortcuts - phrases that immediately evoke a specific theological idea or framework. These "concept handles" are particularly valuable because they represent crystallized theological thinking:
                - **Diagnostic Phrases:** "Chronological snobbery," "therapeutic deism," "Pelagian captivity"
                - **Methodological Concepts:** "Theological triage," "redemptive-historical hermeneutic," "biblical theology"
                - **Programmatic Ideas:** "Cultural mandate," "common grace," "already but not yet"
                - **Traditional Formulations:** "Scripture alone," "by grace alone," "Christ alone"
        - Selection Criteria
            - **Reader-Centered Approach:** Choose terms based on how readers actually search, not just how authors write. Include terms that someone might remember from a half-recalled sermon, lecture, or reading.
            - **Cross-Traditional Vocabulary:** Select terms that bridge denominational and theological boundaries, enabling users from different traditions to find relevant content even when it uses unfamiliar terminology.
            - **Historical Sensitivity:** Include period-appropriate language alongside contemporary terms, recognizing that theological vocabulary evolves over time.
        - Practical Guidelines
            - Select **3-5 terms per chunk** that represent the most likely search terms a user would employ to find this specific content. Prioritize terms that are:
                - Distinctive enough to narrow search results effectively
                - Common enough to be recognizable to your intended audience
                - Varied enough to capture different user vocabularies and search strategies
            - Remember: the goal is discoverability. Choose terms that build bridges between what users know and what they need to find.
        - Use [[I: Terms]]
    - ### Discourse Elements (Fixed)
        - Use ONLY elements from the provided discourse elements framework (113 elements across 8 categories)
        - **NO additions allowed** - use namespaced format: `[[Category/Element]]`
        - **Required**: Every chunk must have at least one discourse element. Typically 3-5 discourse elements per chunk.
        - Categories: Semantic, Logical, Narrative, Personal, Practical, Symbolic, Reference, Structural
        - Example Discourse Elements with Namespaces:
            - [[Logical/Claim]] The author asserts that...
            - [[Semantic/Example]] Illustration of reading Plato vs. commentary
            - [[Symbolic/Metaphor]] "Clean sea breeze of the centuries"
            - [[Personal/Experience]] Lewis recalls his first encounter with...
            - [[Practical/Principle]] After reading a new book, read an old one
            - [[Reference/Commentary]] Explanation of the Athanasian Creed
        - Use [[I: Discourse-Elements]]
    - ### Scripture-References (Fixed)
        - Only add tags if a verse, chapter, or book of the Scriptures (66 books) is mentioned.
        - Normalize: Jn. 3, John 3, and third chapter of John's gospel all become "John 3"
        - Expand: If John 3:16 is mentioned, tag both "John 3" and "John 3:16".
        - For example:
            - Input: "Jn. 3:16"
            - Output: `[[John 3]]`, `[[John 3:16]]`
    - ### Structure-Path (Flexible)
        - Capture the hierarchical location of the chunk within the source document
          
        - Use breadcrumb format: `[[Section > Subsection 1 > Subsection 2]]`- Based on chapter headings, section headings, subheadings, etc.
            - `[[Articles of Affirmation and Denial > Article I]]`
            - `[[Chapter 3 > Abolition of Man]]`
        - Do NOT include source title in the structure-path. All chunks will inherit this from the source metadata.
        - For sources without internal structure, do not add anything to `structure-path`
        - Omit levels that don't exist rather than using empty slots
    - ### Named-Entities (Class Fixed, Entity Flexible)
        - Specific entities are flexible, but they should fall under these 7 classes:
            - Person - Individual human beings (e.g. Augustine of Hippo).
            - Place - Geographic or locational references (e.g. Mount Sinai, Rome).
            - Event - Historical or narrative happenings (e.g. Council of Nicaea, Exodus).
            - Group - Collective entities (e.g. Pharisees, Franciscans, Church of England).
            - Work - Authored or canonical texts (e.g. Confessions, Institutes of the Christian Religion). Period - Temporal spans or eras (e.g. Patristic Era, Reformation).
            - Ideology / Doctrine - Systems of belief (e.g. Arminianism, Predestination).
        - Use namespaced format: `[[Class/Entity]]` (e.g. `[[Person/Augustine of Hippo]]`)
## Sample Chunk and Metadata
    - Chunk: A new book is still on its trial and the amateur is not in a position to judge it. It has to be tested against the great body of Christian thought down the ages, and all its hidden implications (often unsuspected by the author himself have to be brought to light. Often it cannot be fully understood without the knowledge of a good many other modern books. If you join at eleven o'clock a conversation which began at eight you will often not see the real bearing of what is said. Remarks which seem to you very ordinary will produce laughter or irritation and you will not see why the reason, of course, being that the earlier stages of the conversation have given them a special point. In the same way sentences in a modern book which look quite ordinary may be directed af some other book; in this way you may be led to accept what you would have indignantly rejected if you knew its real significance. The only safety is to have a standard of plain, central Christianity ("mere Christianity" as Baxter called it) which puts the controversies of the moment in their proper perspective. Such a standard can be acquired only from the old books. It is a good rule, after reading a new book, never to allow yourself another new one till vou have read an old one in between. If that is too much for you, you should at east read one old one to every three new ones.
        - concepts:: [[Authority]], [[Tradition]], [[Scripture]]
        - topics:: [[Authority/On testing new ideas against established Christian tradition]], [[Tradition/On the role of ancient sources in evaluating contemporary theology]], [[Scripture/On using historical Christianity as interpretive standard]]
        - terms:: [[Mere Christianity]], [[standard of faith]], [[Christian orthodoxy]], [[ancient wisdom]], [[biblical foundation]]
        - discourse-elements::
            - [[Practical/Principle]] "It is a good rule, after reading a new book, never to allow yourself another new one till you have read an old one in between"
            - [[Logical/Argument]] New books must be tested against the great body of Christian thought down the ages
            - [[Symbolic/Metaphor]] Joining a conversation at eleven o'clock that began at eight
            - [[Practical/Problem]] Modern sentences may be directed at other books, leading to unintended acceptance
            - [[Logical/Claim]] Only old books can provide the standard of "mere Christianity" for proper perspective
        - scripture-references::
        - structure-path::
        - named-entities:: [[Person/Richard Baxter]], [[Ideology/Mere Christianity]]
## Quality Guidelines
    1. **Accuracy**: Only use items from the provided indexes unless they are "Flexible"
    2. **Relevance**: Choose the most fitting tags, don't force inappropriate fits. When in doubt about tags, choose the closest available option or leave blank rather than creating new tags for fixed lists.
    3. **Completeness**: Every chunk should have concept, topic, term, and discourse-element. Most will have named-entities. Some will have scripture-reference and structure-path.
    4. **Precision**: Be specific in element descriptions for the discourse-element tags
    5. **Consistency**: Use the same approach across similar content types
## Provided Indexes
    'Index: Concepts.md'
    'Index: Function.md'
    'Index: Topics.md'
    'Index: Terms.md'
