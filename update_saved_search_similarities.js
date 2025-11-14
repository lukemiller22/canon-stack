/**
 * Migration script to update similarity scores in saved searches
 * Run this in the browser console to fix negative similarity scores
 * 
 * Usage: Copy and paste this entire script into the browser console
 */

function updateSavedSearchSimilarities() {
    try {
        // Get saved searches from localStorage
        const searchHistoryJson = localStorage.getItem('searchHistory');
        if (!searchHistoryJson) {
            console.log('No saved searches found');
            return;
        }
        
        const searchHistory = JSON.parse(searchHistoryJson);
        let updatedCount = 0;
        let fixedCount = 0;
        
        // Process each saved search
        for (const search of searchHistory) {
            if (!search.sources || !Array.isArray(search.sources)) {
                continue;
            }
            
            let searchUpdated = false;
            
            // Update similarity scores in sources
            for (const source of search.sources) {
                if (source.relevance_explanation) {
                    // Extract similarity score from relevance explanation
                    // Format: "... (similarity: -0.120)" or "... (similarity: 0.113)"
                    const similarityMatch = source.relevance_explanation.match(/\(similarity:\s*([-\d.]+)\)/);
                    if (similarityMatch) {
                        const oldSimilarity = parseFloat(similarityMatch[1]);
                        
                        // Apply new clamping logic: clamp to [0, 1]
                        const newSimilarity = Math.max(0.0, Math.min(1.0, oldSimilarity));
                        
                        if (oldSimilarity !== newSimilarity) {
                            // Update the relevance explanation
                            source.relevance_explanation = source.relevance_explanation.replace(
                                /\(similarity:\s*[-\d.]+\)/,
                                `(similarity: ${newSimilarity.toFixed(3)})`
                            );
                            
                            // Update similarity_score if it exists
                            if (source.similarity_score !== undefined) {
                                source.similarity_score = newSimilarity;
                            }
                            
                            searchUpdated = true;
                            fixedCount++;
                            console.log(`Fixed similarity: ${oldSimilarity} → ${newSimilarity} in search "${search.query.substring(0, 50)}..."`);
                        }
                    }
                }
                
                // Also update similarity_score field directly if it exists and is negative
                if (source.similarity_score !== undefined && source.similarity_score < 0) {
                    source.similarity_score = Math.max(0.0, Math.min(1.0, source.similarity_score));
                    searchUpdated = true;
                    fixedCount++;
                }
            }
            
            if (searchUpdated) {
                updatedCount++;
            }
        }
        
        // Save updated searches back to localStorage
        if (updatedCount > 0) {
            localStorage.setItem('searchHistory', JSON.stringify(searchHistory));
            console.log(`\n✅ Migration complete!`);
            console.log(`   Updated ${updatedCount} saved searches`);
            console.log(`   Fixed ${fixedCount} similarity scores`);
            console.log(`   All negative similarity scores have been clamped to 0.0`);
        } else {
            console.log('No similarity scores needed updating');
        }
        
        return {
            updatedSearches: updatedCount,
            fixedScores: fixedCount
        };
        
    } catch (error) {
        console.error('Error updating similarity scores:', error);
        return null;
    }
}

// Run the migration
console.log('Starting similarity score migration...');
const result = updateSavedSearchSimilarities();
if (result) {
    console.log('Migration result:', result);
}

