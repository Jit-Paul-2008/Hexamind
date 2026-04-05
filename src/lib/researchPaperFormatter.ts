export interface ResearchPaperMetadata {
  title: string;
  authors: string[];
  abstract: string;
  keywords: string[];
  date: string;
  doi?: string;
}

export class ResearchPaperFormatter {
  static formatTechnicalOutputToPaper(technicalOutput: string, query: string): string {
    // Extract key information from technical output
    const sources = this.extractSources(technicalOutput);
    const findings = this.extractFindings(technicalOutput);
    const methodology = this.extractMethodology(technicalOutput);
    const discussion = this.extractDiscussion(technicalOutput);
    const conclusion = this.extractConclusion(technicalOutput);

    // Generate academic paper structure
    const metadata = this.generateMetadata(query);
    const paper = this.buildPaperStructure(metadata, {
      abstract: this.generateAbstract(query, findings),
      introduction: this.generateIntroduction(query, methodology),
      methodology: this.generateMethodologySection(methodology),
      results: this.generateResultsSection(findings, sources),
      discussion: this.generateDiscussionSection(discussion),
      conclusion: this.generateConclusionSection(conclusion),
      references: this.generateReferences(sources)
    });

    return paper;
  }

  private static extractSources(output: string): Array<{id: string, title: string, url: string, credibility: number}> {
    const sourceRegex = /\| S(\d+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|/g;
    const sources = [];
    let match;
    
    while ((match = sourceRegex.exec(output)) !== null) {
      sources.push({
        id: match[1],
        title: match[2].trim(),
        url: match[5]?.trim() || '',
        credibility: parseFloat(match[4]) || 0
      });
    }
    
    return sources;
  }

  private static extractFindings(output: string): string[] {
    const findings = [];
    
    // Look for key findings sections
    const supportiveMatch = output.match(/### 3\.2 Supportive Findings[\s\S]*?(?=###|$)/);
    if (supportiveMatch) {
      findings.push(supportiveMatch[0]);
    }

    const riskMatch = output.match(/### 3\.3 Risk Factors and Constraints[\s\S]*?(?=###|$)/);
    if (riskMatch) {
      findings.push(riskMatch[0]);
    }

    return findings;
  }

  private static extractMethodology(output: string): string {
    const methodologyMatch = output.match(/## 2\. Methods[\s\S]*?(?=##|$)/);
    return methodologyMatch ? methodologyMatch[0] : '';
  }

  private static extractDiscussion(output: string): string {
    const discussionMatch = output.match(/## 4\. Discussion[\s\S]*?(?=##|$)/);
    return discussionMatch ? discussionMatch[0] : '';
  }

  private static extractConclusion(output: string): string {
    const conclusionMatch = output.match(/## 6\. Conclusion[\s\S]*?(?=##|$)/);
    return conclusionMatch ? conclusionMatch[0] : '';
  }

  private static generateMetadata(query: string): ResearchPaperMetadata {
    return {
      title: this.generateTitle(query),
      authors: ['Hexamind Research System', 'Multi-Agent Analysis'],
      abstract: '',
      keywords: this.generateKeywords(query),
      date: new Date().toISOString().split('T')[0],
      doi: `10.1234/hexamind.${Date.now()}`
    };
  }

  private static generateTitle(query: string): string {
    // Convert query to academic title format
    const title = query
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
    
    // Add academic qualifiers
    if (!title.includes('Analysis') && !title.includes('Study')) {
      return `A Comprehensive Analysis of ${title}`;
    }
    return title;
  }

  private static generateKeywords(query: string): string[] {
    const words = query.toLowerCase().split(' ');
    const keywords = [...words];
    
    // Add academic keywords
    keywords.push('multi-agent analysis');
    keywords.push('research synthesis');
    keywords.push('evidence-based');
    keywords.push('systematic review');
    keywords.push('comprehensive analysis');
    
    return [...new Set(keywords)].slice(0, 6);
  }

  private static generateAbstract(query: string, findings: string[]): string {
    return `This paper presents a comprehensive analysis of ${query.toLowerCase()} using a multi-agent research methodology. 
Through systematic evaluation of multiple sources and expert perspectives, we identify key opportunities, 
challenges, and implications for stakeholders. The analysis reveals ${findings.length > 0 ? 'significant findings' : 'important considerations'} 
that inform both theoretical understanding and practical applications. 
Our approach combines adversarial reasoning with synthesis to provide balanced, evidence-based insights 
that advance the current state of knowledge in this domain.`;
  }

  private static generateIntroduction(query: string, methodology: string): string {
    return `## 1. Introduction

${query.charAt(0).toUpperCase() + query.slice(1)} represents a critical area of contemporary research with significant implications for both theory and practice. 
As technological and methodological advances continue to reshape our understanding of this domain, 
there is growing need for comprehensive, evidence-based analysis that can guide decision-making and future research directions.

The complexity of modern research challenges requires sophisticated analytical approaches that can 
integrate diverse perspectives, evaluate evidence quality, and identify both opportunities and risks. 
Traditional single-perspective analyses often fail to capture the nuanced reality of complex systems, 
leading to incomplete or biased conclusions.

This paper addresses these challenges through a novel multi-agent research methodology that 
systematically examines the topic from multiple analytical perspectives. By combining 
the insights of specialized agents with different analytical frameworks, we provide a more 
comprehensive and balanced understanding of ${query.toLowerCase()}.

The remainder of this paper is organized as follows: Section 2 describes our methodology, 
Section 3 presents the results of our analysis, Section 4 discusses the implications 
of our findings, and Section 5 concludes with recommendations for future research and practice.`;
  }

  private static generateMethodologySection(methodology: string): string {
    return `## 2. Methodology

### 2.1 Research Design

This study employs a novel multi-agent research methodology designed to provide comprehensive analysis 
through adversarial collaboration and synthesis. The approach leverages five specialized agents, 
each contributing unique analytical perspectives:

- **Advocate Agent**: Focuses on opportunity identification and value creation
- **Skeptic Agent**: Emphasizes risk assessment and failure mode analysis  
- **Synthesiser Agent**: Integrates competing perspectives into coherent frameworks
- **Oracle Agent**: Provides scenario forecasting and future outlook
- **Verifier Agent**: Conducts evidence validation and quality assurance

### 2.2 Data Collection and Analysis

Our research methodology incorporates systematic literature review through automated search systems, 
ensuring comprehensive coverage of relevant sources. The analysis process involves:

1. **Source Identification**: Systematic search across multiple databases and repositories
2. **Evidence Evaluation**: Quality assessment of identified sources using established criteria
3. **Multi-Perspective Analysis**: Parallel processing by specialized agents
4. **Synthesis and Validation**: Integration of insights with quality assurance

### 2.3 Quality Assurance

To ensure analytical rigor, we implement multiple quality control mechanisms:
- Source credibility assessment and weighting
- Contradiction identification and explicit preservation
- Evidence-to-claim mapping and validation
- Peer review through adversarial agent interaction

${methodology || 'The analysis follows established protocols for systematic research synthesis and evidence evaluation.'}`;
  }

  private static generateResultsSection(findings: string[], sources: any[]): string {
    let results = `## 3. Results

### 3.1 Evidence Base Overview

Our analysis identified ${sources.length} primary sources spanning multiple domains and perspectives. 
The evidence base includes ${sources.filter(s => s.credibility >= 0.8).length} high-credibility sources 
(credibility ≥ 80%) and ${sources.filter(s => s.credibility < 0.8).length} supplementary sources. 
This diverse evidence base provides a robust foundation for our analysis and conclusions.`;

    if (findings.length > 0) {
      results += '\n\n### 3.2 Key Findings\n\n';
      findings.forEach((finding, index) => {
        const title = this.extractSectionTitle(finding);
        results += `#### 3.2.${index + 1} ${title}\n\n${finding}\n\n`;
      });
    }

    return results;
  }

  private static generateDiscussionSection(discussion: string): string {
    return `## 4. Discussion

${discussion || 'The findings of this analysis contribute to our understanding of the research topic in several important ways. 
The multi-agent approach reveals insights that might be missed through single-perspective analyses, 
demonstrating the value of adversarial collaboration in research synthesis.'}

### 4.1 Theoretical Implications

Our findings advance theoretical understanding by providing a more nuanced view of the research topic. 
The integration of multiple perspectives helps reconcile apparent contradictions and identifies areas 
where current understanding is incomplete.

### 4.2 Practical Implications

For practitioners and decision-makers, this analysis provides evidence-based guidance that can inform 
strategy and implementation decisions. The explicit identification of risks and constraints 
helps stakeholders make more informed choices.

### 4.3 Limitations

This research has several limitations that should be considered when interpreting the results. 
The analysis is constrained by the availability and quality of existing sources, 
and the multi-agent approach, while comprehensive, may introduce systematic biases 
through its analytical frameworks.

### 4.4 Future Research Directions

Several promising directions emerge from this analysis for future research:
- Longitudinal studies to track developments over time
- Comparative analyses across different contexts and populations
- Methodological refinements to improve analytical accuracy
- Expansion of source diversity and coverage`;
  }

  private static generateConclusionSection(conclusion: string): string {
    return `## 5. Conclusion

This paper presented a comprehensive analysis of the research topic using a novel multi-agent methodology. 
Through systematic evaluation of evidence from multiple perspectives, we have identified key insights 
that advance both theoretical understanding and practical application.

${conclusion || 'The analysis demonstrates the value of multi-agent approaches in research synthesis, 
providing more balanced and comprehensive insights than traditional single-perspective methods.'}

### 5.1 Contributions

The main contributions of this work include:
- A novel application of multi-agent systems to research synthesis
- Comprehensive evidence evaluation with explicit quality assessment
- Identification of key opportunities, risks, and implications
- Evidence-based recommendations for practice and future research

### 5.2 Recommendations

Based on our analysis, we recommend:
- Careful consideration of both opportunities and risks in decision-making
- Continued investment in evidence-based approaches to research
- Development of more sophisticated multi-agent analytical systems
- Enhanced focus on source quality and validation in research synthesis

This work provides a foundation for future research in this area and demonstrates the potential 
of advanced analytical methods to improve our understanding of complex topics.`;
  }

  private static generateReferences(sources: any[]): string {
    if (sources.length === 0) {
      return '## References\n\nNo references were available for this analysis.';
    }

    let references = '## References\n\n';
    sources.forEach((source, index) => {
      references += `${index + 1}. ${source.title}. `;
      if (source.url) {
        references += `Available at: ${source.url}. `;
      }
      references += `(Credibility: ${(source.credibility * 100).toFixed(0)}%)\n\n`;
    });

    return references;
  }

  private static extractSectionTitle(content: string): string {
    const titleMatch = content.match(/\*\*([^*]+)\*\*/);
    return titleMatch ? titleMatch[1] : 'Analysis';
  }

  private static buildPaperStructure(metadata: ResearchPaperMetadata, sections: any): string {
    let paper = '';

    // Title and metadata
    paper += `# ${metadata.title}\n\n`;
    paper += `**Authors:** ${metadata.authors.join(', ')}\n`;
    paper += `**Date:** ${metadata.date}\n`;
    paper += `**DOI:** ${metadata.doi}\n`;
    paper += `**Keywords:** ${metadata.keywords.join(', ')}\n\n`;

    // Abstract
    paper += `## Abstract\n\n${sections.abstract}\n\n`;

    // Main sections
    paper += `${sections.introduction}\n\n`;
    paper += `${sections.methodology}\n\n`;
    paper += `${sections.results}\n\n`;
    paper += `${sections.discussion}\n\n`;
    paper += `${sections.conclusion}\n\n`;

    // References
    paper += `${sections.references}\n`;

    return paper;
  }
}
