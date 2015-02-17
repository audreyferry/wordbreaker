import codecs 
import time
import datetime
import operator
import sys
import os
import codecs # for utf8
import string
import copy
import math
from latexTable import MakeLatexTable
import pdb
import pickle

verboseflag = False

# Jan 6: added precision and recall.


class LexiconEntry:
	def __init__(self, key = ""):
		self.m_Key = key
		self.m_ParseCount = 0
		self.m_ReprCount = 0
		self.m_Frequency= 0.0        
		self.m_Subwords = list()
		self.m_Extwords = list() 
		self.m_NewExtwords = list()
		self.m_CountRegister = list()
		
		
	def UpdateRegister(self, current_iteration):
		if len(self.m_CountRegister) > 0:
			last_entry = self.m_CountRegister[-1]
			last_ParseCount = last_entry[1]
			last_ReprCount = last_entry[2]
			if self.m_ParseCount != last_ParseCount or self.m_ReprCount != last_ReprCount or self.m_NewExtwords != []:
				self.m_CountRegister.append((current_iteration, self.m_ParseCount, self.m_ReprCount, self.m_NewExtwords))
		else:
			self.m_CountRegister.append((current_iteration, self.m_ParseCount, self.m_ReprCount, self.m_NewExtwords))


	def Display(self, outfile):
		#print >>outfile, "%s" % self.m_Key		
		print >>outfile, self.m_Key, "   ", self.m_Frequency, "   ", -1* math.log(self.m_Frequency, 2)		
		if len(self.m_Subwords) > 0:
			expression = "/".join( self.m_Subwords )
			print >>outfile, "%s" % expression
                        # NOTE: component subwords are displayed here even if filtered from lexicon; 
			# however repr counts are adjusted (see FilterZeroCountEntries())
  			
		for iteration_number, parse_count, repr_count, newextwords in self.m_CountRegister:
		        if newextwords == []:
		        	print >>outfile, "%6i %10s %5s" % (iteration_number, '{:,}'.format(parse_count), '{:,}'.format(repr_count))
		        else:    
				print >>outfile, "%6i %10s %5s    %-100s" % (iteration_number, '{:,}'.format(parse_count),  '{:,}'.format(repr_count), '{}'.format(newextwords))

# ---------------------------------------------------------#
class Lexicon:
	def __init__(self):
		self.m_EntryDict = dict()
		self.m_SizeOfLongestEntry = 0
		self.m_DeletionDict = dict()    # these are the words that were nominated and then not used in any line-parses *at all*.# They never stop getting nominated.
		self.m_Corpus 	= list()
		self.m_ParsedCorpus = list()
		self.m_CorpusCost = 0.0		# CorpusCost and LexiconCost could be local variables
		self.m_LexiconCost = 0.0
		self.m_InitialLexCost = 0.0
		self.m_TrueDictionary = dict()
		self.m_NumberOfTrueRunningWords = 0
		self.m_BreakPointList = list()
		self.m_PrecisionRecallHistory = list()
	# ---------------------------------------------------------#
	def save_obj(self, obj, filename ):
		fp = open(filename, 'wb')
		pickle.dump(obj, fp, pickle.HIGHEST_PROTOCOL)
		fp.close()
		
	#def load_obj(self, obj, name ):    #CALLING THIS DOESN'T WORK; maybe a deep copy problem?
		#fp = open(name, 'rb')
		#obj = pickle.load(fp)
		#fp.close()

	def SaveState(self):
		self.save_obj(self.m_EntryDict, 'Pkl_EntryDict.p')
		self.save_obj(self.m_SizeOfLongestEntry, 'Pkl_SizeOfLongestEntry.p')
		self.save_obj(self.m_DeletionDict, 'Pkl_DeletionDict.p')
		self.save_obj(self.m_Corpus, 'Pkl_Corpus.p')
		self.save_obj(self.m_ParsedCorpus, 'Pkl_ParsedCorpus.p')
		self.save_obj(self.m_BreakPointList, 'Pkl_BreakPointList.p')
		self.save_obj(self.m_PrecisionRecallHistory, 'Pkl_PrecisionRecallHistory.p')
		
	def LoadState(self, intended_prev_iteration):
		fp = open('Pkl_PrecisionRecallHistory.p', 'rb')
		self.m_PrecisionRecallHistory = pickle.load(fp)
		# self.PrintPrecisionRecall(outfile)
		last_saved_iteration = self.m_PrecisionRecallHistory[-1][0]
		if last_saved_iteration != intended_prev_iteration:
			print "Last saved iteration number was %d. Set 'prev_iteration_number' to match!" % last_saved_iteration
			sys.exit(0)
			
		fp = open('Pkl_EntryDict.p', 'rb')
		self.m_EntryDict = pickle.load(fp)
		fp = open('Pkl_SizeOfLongestEntry.p', 'rb')
		self.m_SizeOfLongestEntry = pickle.load(fp)
		fp = open('Pkl_DeletionDict.p', 'rb')
		self.m_DeletionDict = pickle.load(fp)
		fp = open('Pkl_Corpus.p', 'rb')
		self.m_Corpus = pickle.load(fp)
		fp = open('Pkl_ParsedCorpus.p', 'rb')
		self.m_ParsedCorpus = pickle.load(fp)
		fp = open('Pkl_BreakPointList.p', 'rb')
		self.m_BreakPointList = pickle.load(fp)

		
	# ---------------------------------------------------------#
	def AddEntry(self,key,new_entry):    #was AddEntry(self,key,count)
		#this_entry = LexiconEntry(key,count)
		self.m_EntryDict[key] = new_entry
		if len(key) > self.m_SizeOfLongestEntry:
			self.m_SizeOfLongestEntry = len(key)
	# ---------------------------------------------------------#	
	def FilterZeroCountEntries(self, iteration_number):
		for key, key_entry in self.m_EntryDict.items():
			if len(key)>1 and key_entry.m_ParseCount == 0 and key_entry.m_ReprCount < 2:   # THIS IS A SIMPLE VERSION; ALSO, DO WE REALLY WANT TO DISALLOW ITS USE FOR THE FUTURE?
				# First, maintain consistency of lexicon
				for e in key_entry.m_Extwords:    # there's at most one
					self.m_EntryDict[e].m_Subwords.remove(key)   #on third thought, remember hap, perhap, perhaps # on second thought, retain the original component
				for s in key_entry.m_Subwords:
					s_entry = self.m_EntryDict[s]
					s_entry.m_Extwords.remove(key)
					if key in s_entry.m_NewExtwords:
						s_entry.m_NewExtwords.remove(key)
					s_entry.m_ReprCount -= 1
						
					for e in key_entry.m_Extwords:
						e_entry = self.m_EntryDict[e]
						e_entry.m_Subwords.append(s)
						s_entry.m_Extwords.append(e)
						s_entry.m_ReprCount += 1
				
				# Then transfer this entry from the EntryDict to the DeletionDict
				key_entry.UpdateRegister(iteration_number)      # so that this last stage is visible
				self.m_DeletionDict[key] = key_entry				
				del self.m_EntryDict[key]
				
				print "Deleted ", key
				print >>outfile, "Deleted ", key
	# ---------------------------------------------------------#
	def TrackChanges(self, iteration_number):
	        for key, entry in self.m_EntryDict.iteritems():
	               entry.UpdateRegister(iteration_number)

	# ---------------------------------------------------------#
	#def ReadCorpus(self, infilename):  #2014_07_22  Not in use. 
	#	print "\nName of data file: ", infilename
	#	if not os.path.isfile(infilename):
	#		print "Warning: ", infilename, " does not exist."
	#	if g_encoding == "utf8":
	#		infile = codecs.open(infilename, encoding = 'utf-8')
	#	else:
	#		infile = open(infilename) 	 
	#	self.m_Corpus = infile.readlines() # bad code if the corpus is very large -- but then we won't use python.
	#	for line in self.m_Corpus:			 		 
	#		for letter in line:
	#			if letter not in self.m_EntryDict:
	#				this_lexicon_entry = LexiconEntry()
	#				this_lexicon_entry.m_Key = letter
	#				this_lexicon_entry.m_Count = 1
	#				self.m_EntryDict[letter] = this_lexicon_entry					 
	#			else:
	#				self.m_EntryDict[letter].m_Count += 1
	#	self.m_SizeOfLongestEntry = 1	
	#	self.ComputeDictFrequencies()
	# ---------------------------------------------------------#


	#---------------------------------------------------#
	#  Populates data structures to begin the analysis. #
	#  Records truth for measuring performance.         #
	#---------------------------------------------------#  
	def ReadBrokenCorpus(self, infilename, numberoflines= 0):
		print "\nName of data file: ", infilename
		if not os.path.isfile(infilename):
			print "Warning: ", infilename, " does not exist."
		if g_encoding == "utf8":
			infile = codecs.open(infilename, encoding = 'utf-8')
		else:
			infile = open(infilename) 	 
		 
		rawcorpus_list = infile.readlines() # bad code if the corpus is very large -- but then we won't use python.
		for line in rawcorpus_list:						 	 
			this_line = ""
			breakpoint_list = list()
			
			# LOWERCASE LOWERCASE LOWERCASE LOWERCASE LOWERCASE
			line = line.lower()
			# LOWERCASE LOWERCASE LOWERCASE LOWERCASE LOWERCASE
			
			line = line.replace('.', ' .').replace('?', ' ?')
			line_list = line.split()
			if len(line_list) <=  1:
				continue			 	 
			for word in line_list:
				self.m_NumberOfTrueRunningWords += 1
				if word not in self.m_TrueDictionary:
					self.m_TrueDictionary[word] = 1
				else:
					self.m_TrueDictionary[word] += 1
				this_line += word
				breakpoint_list.append(len(this_line))	

			self.m_Corpus.append(this_line)	
			#for letter in line:       # audrey 2014_07_10. Replace "line" by "this_line" (as below).
                                       # Without this change, every occurrence of '\n', '\r', and ' '
                                       # is counted, which affects the frequency, hence the plog, of 
                                       # the other lexicon items--resulting in an inflated initial
                                       # corpus cost. However, since these three whitespace characters
                                       # themselves never appear in the parse, they get removed
                                       # from the lexicon anyway at the end of the "zeroth" stage. 
                                       # So calculation of corpus cost in further iterations is unaffected.
                                       # NOTE - probably zeroth stage processing can be shortened.
			for letter in this_line:
				if letter not in self.m_EntryDict:
					this_entry = LexiconEntry()
					this_entry.m_Key = letter
					this_entry.m_ParseCount = 1   #counts occurrences of letter in the corpus
					self.AddEntry(letter, this_entry)
				else:
					self.m_EntryDict[letter].m_ParseCount += 1			 
			if numberoflines > 0 and len(self.m_Corpus) > numberoflines:
				break		 
			self.m_BreakPointList.append(breakpoint_list)

		# HERE IS INITIAL LEXICON INFORMATION
		# At this point the only entries in the lexicon are single characters.
		# There are as yet no composite entries to contribute to the cost.
		numSymbols = len(self.m_EntryDict)
		self.m_InitialLexCost = numSymbols * math.log(numSymbols, 2)
		self.m_LexiconCost = self.m_InitialLexCost
		
		# For a given entry e, m_ReprCount tallies the number of other entries in the <<lexicon>> which use e in their composition.
		# So at this point m_ReprCount == 0 for each entry. 
		# Note also that, at this point, for each entry its m_ParseCount records the number of occurrences in the <<corpus>> of a particular single character.

		# LOGICALLY PRIOR TO THE INITIAL PARSE
		self.m_SizeOfLongestEntry = 1	
		for key, entry in self.m_EntryDict.iteritems():	
		        entry.m_CountRegister.append((0, entry.m_ParseCount, 0, []))  # iteration_number|parse count|repr count|new extwords  as in UpdateRegister()
		self.ComputeDictFrequencies()  # determines best coding for pointers to entries

		# HERE IS THE INITIAL PARSE
		for line in self.m_Corpus:
			self.m_ParsedCorpus.append(list(line))    #Parsing is easy!

		# AND ITS COST		
		self.m_CorpusCost = 0.0	
		for key, entry in self.m_EntryDict.iteritems():
			self.m_CorpusCost += entry.m_ParseCount *  -1 * math.log(entry.m_Frequency, 2)
			
	
		print "Cost: "
		print "-%16s" % 'Corpus: ',    "{0:18,.4f}".format(self.m_CorpusCost)
		print "-%16s" % 'Lexicon: ',   "{0:18,.4f}".format(self.m_LexiconCost)
		print "-%16s" % 'Combined: ',  "{0:18,.4f}".format(self.m_CorpusCost + self.m_LexiconCost)
		
		print >>outfile, "Cost: "
		print >>outfile, "-%16s" % 'Corpus: ',    "{0:18,.4f}".format(self.m_CorpusCost)
		print >>outfile, "-%16s" % 'Lexicon: ',   "{0:18,.4f}".format(self.m_LexiconCost)
		print >>outfile, "-%16s" % 'Combined: ',  "{0:18,.4f}".format(self.m_CorpusCost + self.m_LexiconCost)
		
		
		##RECORD THE TRUE DICTIONARY
		#print >>outfile, "\n\nTRUE DICTIONARY\n"
		#for word in sorted(self.m_TrueDictionary.iterkeys()):
		#    print >>outfile,  "%20s %10s" % (word, "{:,}".format(self.m_TrueDictionary[word]))
 
# ---------------------------------------------------------#
	def ComputeDictFrequencies(self):
		TotalCount = 0
		for (key, entry) in self.m_EntryDict.iteritems():
			TotalCount += entry.m_ParseCount + entry.m_ReprCount
		for (key, entry) in self.m_EntryDict.iteritems():
			entry.m_Frequency = (entry.m_ParseCount + entry.m_ReprCount)/float(TotalCount)
			 
# ---------------------------------------------------------#
#	def ComputeDictFrequencies(self, FreqDenom):
#		for (key, entry) in self.m_EntryDict.iteritems():
#			entry.m_Frequency = (entry.m_ParseCount + entry.m_ReprCount)/float(FreqDenom)
#			 
# ---------------------------------------------------------#
	def ParseCorpus(self, outfile, current_iteration):
		self.m_ParsedCorpus = list()
		self.m_CorpusCost = 0.0

		for word, entry in self.m_EntryDict.iteritems():
			entry.m_ParseCount = 0;    #entry.ResetCounts(current_iteration)
		for line in self.m_Corpus:
			parsed_line,bit_cost = 	self.ParseWord(line, outfile)
			self.m_ParsedCorpus.append(parsed_line)
			self.m_CorpusCost += bit_cost
			for word in parsed_line:
				self.m_EntryDict[word].m_ParseCount +=1

		print "Cost: "
		print "-%16s" % 'Corpus: ',    "{0:18,.4f}".format(self.m_CorpusCost)
		print "-%16s" % 'Lexicon: ',   "{0:18,.4f}".format(self.m_LexiconCost)
		print "-%16s" % 'Combined: ',  "{0:18,.4f}".format(self.m_CorpusCost + self.m_LexiconCost)
		
		print >>outfile, "Cost: "
		print >>outfile, "-%16s" % 'Corpus: ',    "{0:18,.4f}".format(self.m_CorpusCost)
		print >>outfile, "-%16s" % 'Lexicon: ',   "{0:18,.4f}".format(self.m_LexiconCost)
		print >>outfile, "-%16s" % 'Combined: ',  "{0:18,.4f}".format(self.m_CorpusCost + self.m_LexiconCost)

		# in preparation for next iteration
		self.FilterZeroCountEntries(current_iteration)  #NOTE - Does not affect self.m_NumberOfHypothesizedRunningWords
		self.ComputeDictFrequencies()  # Not necessary -- we need counts but will use frequency AFTER adding nominees

		return  
# ---------------------------------------------------------#		 	 
	def PrintParsedCorpus(self,outfile):
		for line in self.m_ParsedCorpus:
			PrintList(line,outfile)		
# ---------------------------------------------------------#
	def ParseWord(self, word, outfile):
		wordlength = len(word)	 
		 
		Parse=dict()
		Piece = ""
		LastChunk = ""		 
		BestCompressedLength = dict()
		BestCompressedLength[0] = 0
		CompressedSizeFromInnerScanToOuterScan = 0.0
		LastChunkStartingPoint = 0
		# <------------------ outerscan -----------><------------------> #
		#                  ^---starting point
		# <----prefix?----><----innerscan---------->
		#                  <----Piece-------------->
		if verboseflag: print >>outfile, "\nOuter\tInner"
		if verboseflag: print >>outfile, "scan:\tscan:\tPiece\tFound?"
		for outerscan in range(1,wordlength+1):  
			Parse[outerscan] = list()
			MinimumCompressedSize= 0.0
			startingpoint = 0
			if outerscan > self.m_SizeOfLongestEntry:
				startingpoint = outerscan - self.m_SizeOfLongestEntry
			for innerscan in range(startingpoint, outerscan):
				if verboseflag: print >>outfile,  "\n %3s\t%3s  " %(outerscan, innerscan),				 
				Piece = word[innerscan: outerscan]	 
				if verboseflag: print >>outfile, " %5s"% Piece, 			 
				if Piece in self.m_EntryDict:		
					if verboseflag: print >>outfile,"   %5s" % "Yes.",	
					
					if Piece == word: continue        # TEMPORARY TO TEST "duringthepast"
					
					CompressedSizeFromInnerScanToOuterScan = -1 * math.log( self.m_EntryDict[Piece].m_Frequency, 2 )				
					newvalue =  BestCompressedLength[innerscan]  + CompressedSizeFromInnerScanToOuterScan  
					if verboseflag: print >>outfile,  " %7.3f bits" % (newvalue), 
					if  MinimumCompressedSize == 0.0 or MinimumCompressedSize > newvalue:
						MinimumCompressedSize = newvalue
						LastChunk = Piece
						LastChunkStartingPoint = innerscan
						if verboseflag: print >>outfile,  " %7.3f bits" % (MinimumCompressedSize), 
				else:
					if verboseflag: print >>outfile,"   %5s" % "No. ",
			BestCompressedLength[outerscan] = MinimumCompressedSize
			if LastChunkStartingPoint > 0:
				Parse[outerscan] = list(Parse[LastChunkStartingPoint])
			else:
				Parse[outerscan] = list()
			if verboseflag: print >>outfile, "\n\t\t\t\t\t\t\t\tchosen:", LastChunk,
			Parse[outerscan].append(LastChunk)
			 
		if verboseflag: 
			PrintList(Parse[wordlength], outfile)
		bitcost = BestCompressedLength[outerscan]
		return (Parse[wordlength],bitcost)
# ---------------------------------------------------------#
	def GenerateCandidates(self, howmany, outfile, current_iteration):
	        # NewExtwords for this iteration are set in this function; 
	        # previous entries may be cleared as here (at top of loop) or within TrackChanges() (at bottom of loop)
	        for word, lexicon_entry in self.m_EntryDict.iteritems():
	    	        lexicon_entry.m_NewExtwords = [] 
	    	
		CandidateDict = dict()      # key is the new word, value is a LexiconEntry object
		NomineeList = list()
		for parsed_line in self.m_ParsedCorpus:	 
			for wordno in range(len(parsed_line)-1):
			        word0 = parsed_line[wordno]
			        word1 = parsed_line[wordno + 1]
				candidate = word0 + word1				 		 
				if candidate in self.m_EntryDict:					 
					continue										 
				if candidate in CandidateDict:
					CandidateDict[candidate].m_ParseCount += 1
				else:
					this_entry = LexiconEntry(candidate)
					this_entry.m_ParseCount = 1
					this_entry.m_Subwords = [word0, word1]
					CandidateDict[candidate] = this_entry

		SortableCandidateDict = dict()
		for candidate, lex_entry in CandidateDict.iteritems():
			SortableCandidateDict[candidate] = lex_entry.m_ParseCount      #NOTE THAT lex_entry.m_ReprCount == 0
		EntireCandidateList = sorted(SortableCandidateDict.iteritems(),key=operator.itemgetter(1), reverse=True)

		
		for candidate, count in EntireCandidateList:
			if candidate in self.m_DeletionDict:				 
				continue
			else:				 
				NomineeList.append((candidate, CandidateDict[candidate]))
			if len(NomineeList) == howmany:
				break
				
		print "Nominees:"
		#DeltaPreParseCounts = 0
		#DeltaPreReprCounts  = 0
		latex_data= list()
		latex_data.append("piece   count   subword    subword   status")
		for nominee, entry in NomineeList:
		        # for the new word
			entry.m_CountRegister.append((current_iteration, entry.m_ParseCount, entry.m_ReprCount, []))  # as in UpdateRegister() - only this is pre-parse!
			self.AddEntry(nominee,entry) 
			
			# for the trace
			for word in entry.m_Subwords:
				self.m_EntryDict[word].m_ReprCount += 1
	                	self.m_EntryDict[word].m_Extwords.append(nominee)
	                	self.m_EntryDict[word].m_NewExtwords.append(nominee)  #will go into m_CountRegister to display along with changed counts 
			                                                                                   
			# for display			
		        expr = ""
		        for x in entry.m_Subwords:
		        	expr = expr + "%12s" % (x)
			print "%15s  %10s %-50s" % (nominee, '{:,}'.format(entry.m_ParseCount), expr)
			#print "[", nominee, '{:,}'.format(entry.m_Count), entry.m_Subword0, entry.m_Subword1,"]"
			latex_data.append(nominee +  "\t" + '{:,} {}'.format(entry.m_ParseCount, expr) )
			
		        #DeltaPreParseCounts += entry.m_ParseCount   # NOT NEEDED -- the nominees are in the dictionary
		        #DeltaPreReprCounts  += 2                    # and these repr counts are also in the dictionary

		MakeLatexTable(latex_data,outfile)
		self.ComputeDictFrequencies()
		# Note: This pretends that appearances of the nominees are additional, not replacement, occurrences in a parse.
		
		self.m_LexiconCost = self.m_InitialLexCost	
		for key, entry in self.m_EntryDict.iteritems():
			self.m_LexiconCost += entry.m_ReprCount *  -1 * math.log(entry.m_Frequency, 2)

		
		return NomineeList      # NOTE THAT THE RETURN VALUE IS NOT USED

# ---------------------------------------------------------#
	def Expectation(self):
		self.m_NumberOfHypothesizedRunningWords = 0
		for this_line in self.m_Corpus:
			wordlength = len(this_line)
			ForwardProb = dict()
			BackwardProb = dict()
			Forward(this_line,ForwardProb)
			Backward(this_line,BackwardProb)
			this_word_prob = BackwardProb[0]
			
			if WordProb > 0:
				for nPos in range(wordlength):
					for End in range(nPos, wordlength-1):
						if End- nPos + 1 > self.m_SizeOfLongestEntry:
							continue
						if nPos == 0 and End == wordlength - 1:
							continue
						Piece = this_line[nPos, End+1]
						if Piece in self.m_EntryDict:
							this_entry = self.m_EntryDict[Piece]
							CurrentIncrement = ((ForwardProb[nPos] * BackwardProb[End+1])* this_entry.m_Frequency ) / WordProb
							this_entry.m_Count += CurrentIncrement
							self.m_NumberOfHypothesizedRunningWords += CurrentIncrement			



# ---------------------------------------------------------#
	def Maximization(self):
		for entry in self.m_EntryDict:
			entry.m_Frequency = entry.m_Count / self.m_NumberOfHypothesizedRunningWords

# ---------------------------------------------------------#
	def Forward (self, this_line,ForwardProb):
		ForwardProb[0]=1.0
		for Pos in range(1,Length+1):
			ForwardProb[Pos] = 0.0
			if (Pos - i > self.m_SizeOfLongestEntry):
				break
			Piece = this_line[i,Pos+1]
			if Piece in self.m_EntryDict:
				this_Entry = self.m_EntryDict[Piece]
				vlProduct = ForwardProb[i] * this_Entry.m_Frequency
				ForwardProb[Pos] = ForwardProb[Pos] + vlProduct
		return ForwardProb

# ---------------------------------------------------------#
	def Backward(self, this_line,BackwardProb):
		
		Last = len(this_line) -1
		BackwardProb[Last+1] = 1.0
		for Pos in range( Last, Pos >= 0,-1):
			BackwardProb[Pos] = 0
			for i in range(Pos, i <= Last,-1):
				if i-Pos +1 > m_SizeOfLongestEntry:
					Piece = this_line[Pos, i+1]
					if Piece in self.m_EntryDict[Piece]:
						this_Entry = self.m_EntryDict[Piece]
						if this_Entry.m_Frequency == 0.0:
							continue
						vlProduct = BackwardProb[i+1] * this_Entry.m_Frequency
						BackwardProb[Pos] += vlProduct
		return BackwardProb


# ---------------------------------------------------------#		
	def PrintLexicon(self, outfile):
	        print >>outfile, "\n\nLEXICON with trace information"
                for key in sorted(self.m_EntryDict.iterkeys()):			 
			self.m_EntryDict[key].Display(outfile)
		
		print >>outfile, "\n\nDELETIONS"	
                for key in sorted(self.m_DeletionDict.iterkeys()):			 
			self.m_DeletionDict[key].Display(outfile)

# ---------------------------------------------------------#
	def PrecisionRecall(self, iteration_number, outfile,total_word_count_in_parse):   # total_word_count_in_parse not used
		 
		total_true_positive_for_break = 0
		total_number_of_hypothesized_words = 0
		total_number_of_true_words = 0
		for linenumber in range(len(self.m_BreakPointList)):		 
			truth = list(self.m_BreakPointList[linenumber])			 
			if len(truth) < 2:
				print >>outfile, "Skipping this line:", self.m_Corpus[linenumber]
				continue
			number_of_true_words = len(truth) -1				
			hypothesis = list()  					 
			hypothesis_line_length = 0
			accurate_word_discovery = 0
			true_positive_for_break = 0
			word_too_big = 0
			word_too_small = 0
			real_word_lag = 0
			hypothesis_word_lag = 0
			 
			for piece in self.m_ParsedCorpus[linenumber]:
				hypothesis_line_length += len(piece)
				hypothesis.append(hypothesis_line_length)
			number_of_hypothesized_words = len(hypothesis) 			 

			# state 0: at the last test, the two parses were in agreement
			# state 1: at the last test, truth was # and hypothesis was not
			# state 2: at the last test, hypothesis was # and truth was not
			pointer = 0
			state = 0
			while (len(truth) > 0 and len(hypothesis) > 0):
				 
				next_truth = truth[0]
				next_hypothesis  = hypothesis[0]
				if state == 0:
					real_word_lag = 0
					hypothesis_word_lag = 0					
									
					if next_truth == next_hypothesis:
						pointer = truth.pop(0)
						hypothesis.pop(0)
						true_positive_for_break += 1
						accurate_word_discovery += 1
						state = 0
					elif next_truth < next_hypothesis:						 
						pointer = truth.pop(0)
						real_word_lag += 1
						state = 1
					else: #next_hypothesis < next_truth:						 
						pointer = hypothesis.pop(0)
						hypothesis_word_lag = 1
						state = 2
				elif state == 1:
					if next_truth == next_hypothesis:
						pointer = truth.pop(0)
						hypothesis.pop(0)
						true_positive_for_break += 1
						word_too_big += 1						
						state = 0
					elif next_truth < next_hypothesis:
						pointer = truth.pop(0)
						real_word_lag += 1
						state = 1 #redundantly
					else: 
						pointer = hypothesis.pop(0)
						hypothesis_word_lag += 1
						state = 2
				else: #state = 2
					if next_truth == next_hypothesis:
						pointer = truth.pop(0)
						hypothesis.pop(0)
						true_positive_for_break += 1
						word_too_small +=1
						state = 0
					elif next_truth < next_hypothesis:
						pointer = truth.pop(0)
						real_word_lag += 1
						state = 1
					else:
						pointer = hypothesis.pop(0)
						hypothesis_word_lag += 1
						state =2 						
			 			 
 
	
					
			precision = float(true_positive_for_break) /  number_of_hypothesized_words 
			recall    = float(true_positive_for_break) /  number_of_true_words 			
			 		
			total_true_positive_for_break += true_positive_for_break
			total_number_of_hypothesized_words += number_of_hypothesized_words
			total_number_of_true_words += number_of_true_words



		# the following calculations are precision and recall *for breaks* (not for morphemes)
		total_break_precision = float(total_true_positive_for_break) /  total_number_of_hypothesized_words 
		total_break_recall    = float(total_true_positive_for_break) /  total_number_of_true_words 	
		print "Precision  %6.4f; Recall  %6.4f" %(total_break_precision ,total_break_recall)
		print >>outfile, "Precision", total_break_precision, "recall", total_break_recall
		print >>outfile, "\n***"
		self.m_PrecisionRecallHistory.append((iteration_number,  total_break_precision,total_break_recall))

		# precision for word discovery:
		if (False):
			true_positives = 0
			for (word, this_words_entry) in self.m_EntryDict.iteritems():
				if word in self.m_TrueDictionary:
					true_count = self.m_TrueDictionary[word]
					these_true_positives = min(hypothetical_count, this_words_entry.m_Count)
				else:
					these_true_positives = 0
				true_positives += these_true_positives
			word_recall = float(true_positives) / self.m_NumberOfTrueRunningWords
			word_precision = float(true_positives) / self.m_NumberofHypothesizedRunningWords

			print >>outfile, "\n\n***\n"
			print >>outfile, "Word Precision", word_precision, "recall", word_recall
			print "Word Precision  %6.4f; Word Recall  %6.4f" %(word_precision ,word_recall)



# ---------------------------------------------------------#
	def PrintPrecisionRecall(self,outfile):	
		print >>outfile, "\n\nBreak precision and recall"
		for iterno, precision,recall in self.m_PrecisionRecallHistory:
			print >>outfile,"%3d %8.3f  %8.3f" %(iterno, precision , recall)
	
			

# ---------------------------------------------------------#
def PrintList(my_list, outfile):
	print >>outfile
	for item in my_list:
		print >>outfile, item,  


############ USER SETTINGS ##################
total_word_count_in_parse =0
g_encoding =  "asci"  
prev_iteration_number =  10   # Index of last saved iteration ('0' for fresh start)
stop_iteration_number =  12   # Index of last iteration to perform in this run (so #cycles for this run = stop_iteration_number - prev_iteration_number) 
howmanycandidatesperiteration = 25
numberoflines =  0
corpusfilename = "../../data/english/browncorpus.txt"
outfilename = "wordbreaker-brownC-" + str(prev_iteration_number+1) + "i.." + str(stop_iteration_number) + "i.txt"
outfile 	= open (outfilename, "w")
#############################################

current_iteration = prev_iteration_number
this_lexicon = Lexicon()

if prev_iteration_number == 0:
	this_lexicon.ReadBrokenCorpus (corpusfilename, numberoflines)   # audrey 2014_07_04. Note that numberoflines == 0, so all lines get read.
	#this_lexicon.ParseCorpus (outfile, current_iteration)
else:
	print "LOADING SAVED STATE..."
	this_lexicon.LoadState(prev_iteration_number)


t_start = time.time()          # 2014_07_20
print "\nt_start = ", t_start

for current_iteration in range(1+prev_iteration_number, 1+stop_iteration_number):
	print "\nIteration number", current_iteration
	print >>outfile, "\nIteration number", current_iteration
	this_lexicon.GenerateCandidates(howmanycandidatesperiteration, outfile, current_iteration)
	this_lexicon.ParseCorpus (outfile, current_iteration)
	this_lexicon.PrecisionRecall(current_iteration, outfile,total_word_count_in_parse)
	this_lexicon.TrackChanges(current_iteration)
	
this_lexicon.PrintParsedCorpus(outfile)     # COMMENTED OUT  apf 2014_05_29
this_lexicon.PrintLexicon(outfile)
this_lexicon.PrintPrecisionRecall(outfile)

t_end = time.time()
print "\nt_end = ", t_end
print >>outfile, "\nElapsed wall time in seconds = ", t_end - t_start

# EXAMPLE apf 2014_05_20 #
print >>outfile, "\n\n--------------------\n\n"
print >>outfile, "EXAMPLE: Parse 'therentisdue'"
verboseflag = True
this_lexicon.ParseWord("therentisdue", outfile)
# ------------------ #
print >>outfile, "\n\n--------------------\n\n"
print >>outfile, "EXAMPLE: Parse 'duringthepast'"
this_lexicon.ParseWord("duringthepast", outfile)

print >>outfile, "\n\n--------------------\n\n"
print >>outfile, "EXAMPLE: Parse 'duringthe'"
this_lexicon.ParseWord("duringthe", outfile)


print
outfile.close()

print "SAVING...Move to a separate labelled directory if desired to prevent subsequent overwriting"
this_lexicon.SaveState()









