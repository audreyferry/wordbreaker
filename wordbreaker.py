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

verboseflag = False

# Jan 6: added precision and recall.


class LexiconEntry:
	def __init__(self, key = "", count = 0):
		self.m_Key = key              # m_Key, m_Subwords are fixed
		self.m_Count = count          # m_Count, m_Frequency, m_Extwords are recalculated from scratch at each iteration 
		self.m_Frequency= 0.0         # m_CountRegister gets extended when needed to record changes
		self.m_Subwords = ()
		self.m_Extwords = list()      
		self.m_CountRegister = list()
		
		
	def RecordCountAndTrace(self, current_iteration):
		if len(self.m_CountRegister) > 0:
			last_count = self.m_CountRegister[-1][1]
			if self.m_Count != last_count or self.m_Extwords != []:
				self.m_CountRegister.append((current_iteration, self.m_Count, self.m_Extwords))
		else:
			self.m_CountRegister.append((current_iteration, self.m_Count, self.m_Extwords))


	def Display(self, outfile):
		print >>outfile, "%-20s" % self.m_Key
		for iteration_number, count, extwords in self.m_CountRegister:
		        if extwords == []:
		            print >>outfile, "%6i %10s" % (iteration_number, "{:,}".format(count))
		        else:    
			    print >>outfile, "%6i %10s    %-100s" % (iteration_number, "{:,}".format(count), "{}".format(extwords))
# ---------------------------------------------------------#
class Lexicon:
	def __init__(self):
		#self.m_EntryList = list()
		self.m_EntryDict = dict()
		self.m_TrueDictionary = dict()
		self.m_Corpus 	= list()
		self.m_SizeOfLongestEntry = 0
		self.m_CorpusCost = 0.0
		self.m_ParsedCorpus = list()
		self.m_NumberOfHypothesizedRunningWords = 0
		self.m_NumberOfTrueRunningWords = 0
		self.m_BreakPointList = list()
		#self.m_DeletionList = list()  # these are the words that were nominated and then not used in any line-parses *at all*.
		self.m_DeletionDict = dict()  # They never stop getting nominated.
		self.m_PrecisionRecallHistory = list()
	# ---------------------------------------------------------#
	def AddEntry(self,key,count):
		this_entry = LexiconEntry(key,count)
		self.m_EntryDict[key] = this_entry
		if len(key) > self.m_SizeOfLongestEntry:
			self.m_SizeOfLongestEntry = len(key)
	# ---------------------------------------------------------#	
	def FilterZeroCountEntries(self, iteration_number):
		for key, entry in self.m_EntryDict.items():
			if entry.m_Count == 0:
				#self.m_DeletionList.append((key, iteration_number))
				self.m_DeletionDict[key] = iteration_number   # was 1
				del self.m_EntryDict[key]
	# ---------------------------------------------------------#
	def UpdateRegister(self, iteration_number):
	        for key, entry in self.m_EntryDict.iteritems():
	               entry.RecordCountAndTrace(iteration_number)
	# ---------------------------------------------------------#
	#def ReadCorpus(self, infilename):  #2014_07_22  Not in use. If used, note ComputeDictFrequencies(X) needs total of m_Counts over all lexicon entries
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
					this_lexicon_entry = LexiconEntry()
					this_lexicon_entry.m_Key = letter
					this_lexicon_entry.m_Count = 1
					self.m_EntryDict[letter] = this_lexicon_entry					 
				else:
					self.m_EntryDict[letter].m_Count += 1			 
			if numberoflines > 0 and len(self.m_Corpus) > numberoflines:
				break		 
			self.m_BreakPointList.append(breakpoint_list)
		
		self.m_CorpusCost = 0.0	
		self.m_NumberOfHypothesizedRunningWords = 0
		for key, entry in self.m_EntryDict.iteritems():	
		        entry.m_CountRegister.append((0, entry.m_Count, []))  # as in RecordCountAndTrace - but pre-parse!	
		        self.m_NumberOfHypothesizedRunningWords += entry.m_Count 	
		self.m_SizeOfLongestEntry = 1	
		#self.ComputeDictFrequencies()
		self.ComputeDictFrequenciesRelTokenCount(self.m_NumberOfHypothesizedRunningWords)
		
		for key, entry in self.m_EntryDict.iteritems():
			self.m_CorpusCost += entry.m_Count *  -1 * math.log(entry.m_Frequency)
		print "Corpus cost: ", "{:,}".format(self.m_CorpusCost)
		print >>outfile, "Corpus cost: ", "{:,}".format(self.m_CorpusCost)
		
		for line in self.m_Corpus:
			self.m_ParsedCorpus.append(list(line))    #could do this in line loop above
		
		
		##RECORD THE TRUE DICTIONARY
		#print >>outfile, "\n\nTRUE DICTIONARY\n"
		#for word in sorted(self.m_TrueDictionary.iterkeys()):
		#    print >>outfile,  "%20s %10s" % (word, "{:,}".format(self.m_TrueDictionary[word]))
 
# ---------------------------------------------------------#
	#def ComputeDictFrequencies(self):
	#	TotalCount = 0
	#	for (key, entry) in self.m_EntryDict.iteritems():
	#		TotalCount += entry.m_Count
	#	for (key, entry) in self.m_EntryDict.iteritems():
	#		entry.m_Frequency = entry.m_Count/float(TotalCount)
			 
# ---------------------------------------------------------#
	def ComputeDictFrequenciesRelTokenCount(self, token_count):
		for (key, entry) in self.m_EntryDict.iteritems():
			entry.m_Frequency = entry.m_Count/float(token_count)
			 
# ---------------------------------------------------------#
	def ParseCorpus(self, outfile, current_iteration):
		self.m_ParsedCorpus = list()
		self.m_CorpusCost = 0.0	
		self.m_NumberOfHypothesizedRunningWords = 0
		#total_word_count_in_parse = 0	

		for word, lexicon_entry in self.m_EntryDict.iteritems():
			lexicon_entry.m_Count = 0;    #lexicon_entry.ResetCounts(current_iteration)

		for line in self.m_Corpus:	
			parsed_line,bit_cost = 	self.ParseWord(line, outfile)	 
			self.m_ParsedCorpus.append(parsed_line)
			self.m_CorpusCost += bit_cost
			for word in parsed_line:
				self.m_EntryDict[word].m_Count +=1
				self.m_NumberOfHypothesizedRunningWords += 1
		self.FilterZeroCountEntries(current_iteration)  #NOTE - Does not affect self.m_NumberOfHypothesizedRunningWords
		#self.ComputeDictFrequencies()
		self.ComputeDictFrequenciesRelTokenCount(self.m_NumberOfHypothesizedRunningWords)
		print "Corpus cost: ", "{:,}".format(self.m_CorpusCost)
		print >>outfile, "Corpus cost: ", "{:,}".format(self.m_CorpusCost)
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
					CompressedSizeFromInnerScanToOuterScan = -1 * math.log( self.m_EntryDict[Piece].m_Frequency )				
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
	        # Extwords for this iteration are set in this function; 
	        # previous entries may be cleared as here (at top of loop) or within UpdateRegister() (at bottom of loop)
	        for word, lexicon_entry in self.m_EntryDict.iteritems():
	    	        lexicon_entry.m_Extwords = [] 
	    	
		Nominees = dict()      # key is the new word, value is triple consisting of count and the two component words
		NomineeList = list()
		for parsed_line in self.m_ParsedCorpus:	 
			for wordno in range(len(parsed_line)-1):
			        word1 = parsed_line[wordno]
			        word2 = parsed_line[wordno + 1]
				candidate = word1 + word2				 		 
				if candidate in self.m_EntryDict:					 
					continue										 
				if candidate in Nominees:
				        count = Nominees[candidate][0]
				        count += 1
					Nominees[candidate] = (count, word1, word2)
				else:
					Nominees[candidate] = (1, word1, word2)					 
		EntireNomineeList = sorted(Nominees.iteritems(),key=operator.itemgetter(1),reverse=True)
		for nominee, info in EntireNomineeList:
			if nominee  in self.m_DeletionDict:				 
				continue
			else:				 
				NomineeList.append((nominee,info))
			if len(NomineeList) == howmany:
				break
				
		print "Nominees:"
		TotalNomCounts = 0
		latex_data= list()
		latex_data.append("piece   count   subword    subword   status")
		for nominee, info in NomineeList:
		        # for the new word
			self.AddEntry(nominee,info[0])  # SHOULD WE ADD SUBWORDS HERE?
			self.m_EntryDict[nominee].m_Subwords = (info[1], info[2])
	                self.m_EntryDict[nominee].m_CountRegister.append((current_iteration, info[0], []))  # as in RecordCountAndTrace - but pre-parse!   
			
			# for the trace
	                self.m_EntryDict[info[1]].m_Extwords.append(nominee)
	                self.m_EntryDict[info[2]].m_Extwords.append(nominee)
			                                                                                   
			# for display			
			print "[", nominee, '{:,} {} {}'.format(*info),"]"
#			print "[", nominee, info[0], info[1], info[2],"]"
			latex_data.append(nominee +  "\t" + '{:,} {} {}'.format(*info) )
			
		        TotalNomCounts += info[0]

		MakeLatexTable(latex_data,outfile)
		#self.ComputeDictFrequencies()
		self.ComputeDictFrequenciesRelTokenCount(self.m_NumberOfHypothesizedRunningWords + TotalNomCounts)
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
		
		print >>outfile, "\n\nDELETION LIST"	
		for key in self.m_DeletionDict:
			print >>outfile, self.m_DeletionDict[key], key

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



total_word_count_in_parse =0
g_encoding =  "asci"  
numberofcycles = 4   #4    #101    #26    #11
howmanycandidatesperiteration = 25
numberoflines =  0
corpusfilename = "../../data/english/browncorpus.txt"
outfilename = "wordbreaker-brownC-" + str(numberofcycles) + "i.txt" 	
outfile 	= open (outfilename, "w")

t_start = time.time()          # 2014_07_20
print "\nt_start = ", t_start

current_iteration = 0	
this_lexicon = Lexicon()
this_lexicon.ReadBrokenCorpus (corpusfilename, numberoflines)   # audrey 2014_07_04. Note that numberoflines == 0, so all lines get read. 
#this_lexicon.ParseCorpus (outfile, current_iteration)


for current_iteration in range(1, numberofcycles):
	print "\nIteration number", current_iteration
	print >>outfile, "\nIteration number", current_iteration
	this_lexicon.GenerateCandidates(howmanycandidatesperiteration, outfile, current_iteration)
	this_lexicon.ParseCorpus (outfile, current_iteration)
	this_lexicon.PrecisionRecall(current_iteration, outfile,total_word_count_in_parse)
	this_lexicon.UpdateRegister(current_iteration)
	
# this_lexicon.PrintParsedCorpus(outfile)     # COMMENTED OUT  apf 2014_05_29
this_lexicon.PrintLexicon(outfile)
this_lexicon.PrintPrecisionRecall(outfile)

t_end = time.time()
print "\nt_end = ", t_end
print >>outfile, "Elapsed wall time in seconds = ", t_end - t_start

# EXAMPLE apf 2014_05_20 #
print >>outfile, "\n\n--------------------\n\n"
print >>outfile, "EXAMPLE: Parse 'therentisdue'"
verboseflag = True
this_lexicon.ParseWord("therentisdue", outfile);
# ------------------ #

print
outfile.close()








