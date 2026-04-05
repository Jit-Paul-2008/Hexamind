// Simple research paper formatter for V1
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
    // Simple academic paper structure
    const metadata = this.generateMetadata(query);
    
    let paper = `# ${metadata.title}\n\n`;
    paper += `**Authors:** ${metadata.authors.join(', ')}\n`;
    paper += `**Date:** ${metadata.date}\n`;
    paper += `**DOI:** ${metadata.doi}\n`;
    paper += `**Keywords:** ${metadata.keywords.join(', ')}\n\n`;
    
    // Abstract
    paper += `## Abstract\n\n${technicalOutput}\n\n`;
    
    return paper;
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
    const title = query
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
    
    if (!title.includes('Analysis') && !title.includes('Study')) {
      return `A Comprehensive Analysis of ${title}`;
    }
    return title;
  }

  private static generateKeywords(query: string): string[] {
    return query.toLowerCase().split(' ');
  }
}
