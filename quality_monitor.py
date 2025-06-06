# quality_monitor.py - Working Quality Monitor

import json
import re
import time
from datetime import datetime
from pathlib import Path

class AnswerQualityMonitor:
    """Simple but effective quality monitor"""
    
    def __init__(self):
        self.log_file = Path("logs/answer_quality.jsonl")
        self.log_file.parent.mkdir(exist_ok=True)
    
    def log_answer_quality(self, question, answer_data, retrieval_data):
        """Log quality data"""
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "question_length": len(question),
            
            # Retrieval Quality
            "num_results": len(retrieval_data.get("documents", [])),
            "best_distance": min(retrieval_data.get("distances", [99])) if retrieval_data.get("distances") else 99,
            "avg_distance": sum(retrieval_data.get("distances", [99])) / max(1, len(retrieval_data.get("distances", []))),
            
            # Answer Quality
            "answer_length": len(answer_data.get("answer", "")),
            "confidence": answer_data.get("confidence", "unknown"),
            "sources_count": len(answer_data.get("sources", [])),
            
            # Content Analysis
            "has_specific_numbers": bool(re.search(r'\d+', answer_data.get("answer", ""))),
            "has_legal_terms": bool(re.search(r'\b(artikel|absatz|bestimmt|regelt|darf|muss)\b', 
                                            answer_data.get("answer", ""), re.IGNORECASE)),
            
            # Full data for debugging
            "full_answer": answer_data.get("answer", ""),
            "sources": answer_data.get("sources", [])
        }
        
        # Append to log file
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    def analyze_quality_trends(self):
        """Analyze quality trends"""
        
        if not self.log_file.exists():
            print("❌ No logs found")
            return
        
        entries = []
        with open(self.log_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        entries.append(json.loads(line))
                    except:
                        continue
        
        if not entries:
            print("❌ No valid log entries found")
            return
        
        print(f"📊 QUALITY ANALYSIS ({len(entries)} questions)")
        print("=" * 50)
        
        # Confidence Distribution
        confidence_counts = {}
        for entry in entries:
            conf = entry.get("confidence", "unknown")
            confidence_counts[conf] = confidence_counts.get(conf, 0) + 1
        
        print("🎯 CONFIDENCE DISTRIBUTION:")
        for conf, count in sorted(confidence_counts.items()):
            percentage = (count / len(entries)) * 100
            print(f"   {conf}: {count} ({percentage:.1f}%)")
        
        # Average Distances
        distances = [e.get("best_distance", 99) for e in entries if e.get("best_distance", 99) < 90]
        if distances:
            print(f"\n📏 RETRIEVAL QUALITY:")
            print(f"   Average best distance: {sum(distances)/len(distances):.3f}")
            print(f"   Best distance overall: {min(distances):.3f}")
            print(f"   Worst distance: {max(distances):.3f}")
        
        # Answer Quality Indicators
        specific_answers = sum(1 for e in entries if e.get("has_specific_numbers", False))
        legal_terms = sum(1 for e in entries if e.get("has_legal_terms", False))
        
        print(f"\n📝 ANSWER QUALITY:")
        print(f"   With specific numbers: {specific_answers} ({specific_answers/len(entries)*100:.1f}%)")
        print(f"   With legal terms: {legal_terms} ({legal_terms/len(entries)*100:.1f}%)")
        
        # Recent Issues
        recent_entries = entries[-5:] if len(entries) > 5 else entries
        recent_low_quality = [e for e in recent_entries 
                             if e.get("confidence") in ["low", "honest"]]
        
        if recent_low_quality:
            print(f"\n⚠️ RECENT ISSUES ({len(recent_low_quality)} of {len(recent_entries)}):")
            for entry in recent_low_quality[:2]:
                print(f"   Q: {entry['question'][:50]}...")
                print(f"   Confidence: {entry.get('confidence')}, Distance: {entry.get('best_distance', 'N/A'):.3f}")
                print()
    
    def get_improvement_suggestions(self):
        """Get improvement suggestions based on logs"""
        
        if not self.log_file.exists():
            return []
        
        entries = []
        with open(self.log_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        entries.append(json.loads(line))
                    except:
                        continue
        
        if len(entries) < 3:
            return ["Collect more test data for analysis"]
        
        suggestions = []
        
        # High distance average
        avg_distance = sum(e.get("best_distance", 99) for e in entries) / len(entries)
        if avg_distance > 1.5:
            suggestions.append(f"🔧 High average distance ({avg_distance:.2f}) - check embedding model or chunking")
        
        # Low confidence rate
        high_conf_rate = sum(1 for e in entries if e.get("confidence") == "high") / len(entries)
        if high_conf_rate < 0.3:
            suggestions.append(f"🔧 Only {high_conf_rate*100:.1f}% high confidence - adjust thresholds")
        
        # Low legal terms rate
        legal_rate = sum(1 for e in entries if e.get("has_legal_terms", False)) / len(entries)
        if legal_rate < 0.5:
            suggestions.append(f"🔧 Only {legal_rate*100:.1f}% answers contain legal terms - improve content extraction")
        
        return suggestions if suggestions else ["✅ Quality looks good - continue monitoring"]

if __name__ == "__main__":
    monitor = AnswerQualityMonitor()
    monitor.analyze_quality_trends()
    
    suggestions = monitor.get_improvement_suggestions()
    if suggestions:
        print("\n💡 IMPROVEMENT SUGGESTIONS:")
        for suggestion in suggestions:
            print(f"   {suggestion}")