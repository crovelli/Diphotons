#!/bin/env python

from diphotons.Utils.pyrapp import *
from optparse import OptionParser, make_option
from copy import deepcopy as copy
import os, json

from pprint import pprint

import array

from getpass import getuser

from templates_maker import TemplatesApp

import random

from math import sqrt

## ----------------------------------------------------------------------------------------------------------------------------------------
class BiasApp(TemplatesApp):
    """
    Class to handle template fitting.
    Takes care of preparing templates starting from TTrees.
    Inherith from PyRapp and PlotApp classes.
    """
    
    ## ------------------------------------------------------------------------------------------------------------
    def __init__(self):
        
        super(BiasApp,self).__init__(
            option_groups=[
                ("Bias study options", [
                        make_option("--throw-toys",dest="throw_toys",action="store_true",default=False,
                                    help="Throw toy MC",
                                    ),
                        make_option("--binned-toys",dest="binned_toys",action="store_true",default=False,
                                    help="Use binned toys",
                                    ),
                        make_option("--throw-from-model",dest="throw_from_model",action="store_true",default=False,
                                    help="Throw toys from fit to full dataset",
                                    ),
                        make_option("--lumi-factor",dest="lumi_factor",action="store",default=1.,type="float",
                                    help="Luminosity normalization factor",
                                    ),
                        make_option("--fit-toys",dest="fit_toys",action="store_true",default=False,
                                    help="Fit toy MC",
                                    ),
                        make_option("--plot-toys-fits",dest="plot_toys_fits",action="store_true",default=False,
                                    help="Make plots with fit results",
                                    ),
                        make_option("--n-toys",dest="n_toys",action="store",type="int",default=False,
                                    help="Number of toys",
                                    ),
                        make_option("--first-toy",dest="first_toy",action="store",type="int",default=False,
                                    help="First toy to fit",
                                    ),
                        make_option("--components",dest="components",action="callback",type="string",
                                    callback=optpars_utils.ScratchAppend(),
                                    default=[""],
                                    help="MC truth components to be considered in the fit default : [%default]",
                                    ),
                        make_option("--models",dest="models",action="callback",type="string",
                                    callback=optpars_utils.ScratchAppend(),
                                    default=[""],
                                    help="Background models to use default : [%default]",
                                    ),
                        make_option("--observable",dest="observable",action="store",type="string",
                                    default="mass[235,300,5000]",
                                    help="Observable used in the fit default : [%default]",
                                    ),
                        make_option("--fit-range",dest="fit_range",action="callback",type="string",callback=optpars_utils.ScratchAppend(float),
                                    default=[300,500],
                                    help="Observable range for the fit region : [%default]",
                                    ),
                        make_option("--test-range",dest="test_ranges",action="callback",type="string",callback=optpars_utils.ScratchAppend(float),
                                    default=[1000.,5000.],
                                    help="Observable range for the test region : [%default]",
                                    ),
                        make_option("--exclude-test-range",dest="exclude_test_range",action="store_true",default=False,
                                    help="Exclude test range from fit",
                                    ),
                        make_option("--fit",dest="fit",action="store",type="string",
                                    default="2D",
                                    help="Fit to consider"),
                        make_option("--analyze-bias",dest="analyze_bias",action="store_true",default=False),
                        make_option("--bias-files",dest="bias_files",action="callback",type="string",callback=optpars_utils.ScratchAppend(str),
                                    default=[]
                                    ),
                        make_option("--bias-labels",dest="bias_labels",action="callback",type="string",callback=optpars_utils.ScratchAppend(str),
                                    default=[]
                                    ),                        
                        ]
                 )
                ]
            )
        
        ## load ROOT (and libraries)
        global ROOT, style_utils
        import ROOT
        import diphotons.Utils.pyrapp.style_utils as style_utils
        ROOT.gSystem.Load("libdiphotonsUtils")


        self.pdfPars_ = ROOT.RooArgSet()

    def __call__(self,options,args):
        

        ## load ROOT style
        self.loadRootStyle()
        ROOT.TGaxis.SetMaxDigits(3)
        from ROOT import RooFit

        printLevel = ROOT.RooMsgService.instance().globalKillBelow()
        ROOT.RooMsgService.instance().setGlobalKillBelow(RooFit.FATAL)

        options.only_subset = [options.fit]
        
        if len(options.only_subset)>0:
            subset = {}
            for name,fit in options.fits.iteritems():
                if not name in options.only_subset:
                    continue
                subset[name] = fit
            options.fits = subset

        if options.store_new_only:
            self.store_new_ = True
        
        if not options.output_file:
            if options.read_ws: 
                options.output_file = options.read_ws
            else : 
                options.output_file = "templates.root"
        
        if options.read_ws:
            self.readWs(options,args)
        elif not options.analyze_bias:
            self.prepareTemplates(options,args)

        
        if options.throw_toys:
            self.throwToys(options,args)
        
        if options.fit_toys:
            self.fitToys(options,args)

        if options.analyze_bias:
            self.analyzeBias(options,args)
            
    ## ------------------------------------------------------------------------------------------------------------
    def throwToys(self,options,args):
        
        fitname = options.fit
        fit = options.fits[fitname]
        
        roobs = self.buildRooVar(*(self.getVar(options.observable)))
        roowe = self.buildRooVar("weight",[])
        
        for comp,model in zip(options.components,options.models):
            if comp != "":
                comp = "%s_" % comp
            for cat in fit["categories"]:
                                
                treename = "mctruth_%s%s_%s" % (comp,fitname,cat)
                
                print treename
                dset = self.rooData(treename)
                
                reduced = dset.reduce(ROOT.RooArgSet(roobs))
                binned = reduced.binnedClone()
                
                if options.throw_from_model:
                    print "Throwing toys from fit to full dataset"

                    pdf = self.buildPdf(model,"full_%s%s" % (comp,cat), roobs )
                    norm = self.buildRooVar("full_norm_%s_%s%s" %  (model,comp,cat), [], importToWs=False )
                    norm.setVal(dset.sumEntries())
                    extpdf = ROOT.RooExtendPdf("ext_%s_%s%s" %  (model,comp,cat),"ext_%s_%s%s" %  (model,comp,cat),pdf,norm)
                    extpdf.fitTo(binned,ROOT.RooFit.Strategy(2))
                    extpdf.fitTo(reduced,ROOT.RooFit.Strategy(1))
                    
                    ## freeze parameters before importing
                    deps = pdf.getDependents(self.pdfPars_)
                    itr = deps.createIterator()
                    var = itr.Next()
                    while var:
                        var.setConstant(True)
                        var = itr.Next()
                    
                    frame = roobs.frame()
                    binned.plotOn(frame)
                    extpdf.plotOn(frame)
                    

                    resid  = roobs.frame()
                    hist   = frame.getObject(int(frame.numItems()-2))
                    fit    = frame.getObject(int(frame.numItems()-1))
                    hresid = frame.residHist(hist.GetName(),fit.GetName(),True)
                    resid.addPlotable(hresid,"PE")
                    
                    canv = ROOT.TCanvas("full_fit_%s_%s%s" % (model,comp,cat), "full_fit_%s_%s%s" % (model,comp,cat) )
                    canv.Divide(1,2)
                    
                    canv.cd(1)
                    ROOT.gPad.SetPad(0.,0.35,1.,1.)
                    ROOT.gPad.SetLogy()
                    ROOT.gPad.SetLogx()

                    canv.cd(2)
                    ROOT.gPad.SetPad(0.,0.,1.,0.35)
                    
                    canv.cd(1)
                    frame.GetXaxis().SetMoreLogLabels()
                    frame.GetYaxis().SetLabelSize( frame.GetYaxis().GetLabelSize() * canv.GetWh() / ROOT.gPad.GetWh() )
                    frame.GetYaxis().SetRangeUser( 1.e-6,50. )
                    frame.Draw()

                    canv.cd(2)
                    ROOT.gPad.SetGridy()
                    ROOT.gPad.SetLogx()
                    resid.GetXaxis().SetMoreLogLabels()
                    resid.GetYaxis().SetTitleSize( frame.GetYaxis().GetTitleSize() * 6.5/3.5 )
                    resid.GetYaxis().SetTitleOffset( frame.GetYaxis().GetTitleOffset() * 6.5/3.5 )
                    resid.GetYaxis().SetLabelSize( frame.GetYaxis().GetLabelSize() * 6.5/3.5 )
                    resid.GetXaxis().SetTitleSize( frame.GetXaxis().GetTitleSize() * 6.5/3.5 )
                    resid.GetXaxis().SetLabelSize( frame.GetXaxis().GetLabelSize() * 6.5/3.5 )
                    resid.GetYaxis().SetTitle("pull")
                    resid.GetYaxis().SetRangeUser( -5., 5. )
                    resid.Draw()
                    
                    
                    self.keep(canv)
                    self.autosave(True)
                    
                else:
                    pdf = ROOT.RooHistPdf(treename,treename,ROOT.RooArgSet(roobs),binned)
                    norm = self.buildRooVar("norm_%s" %  treename, [], importToWs=False )
                    norm.setVal(dset.sumEntries())
                    print norm.getVal()
                    extpdf = ROOT.RooExtendPdf("ext_%s" %  treename, "ext_%s" %  treename, pdf, norm)
                    print norm.getVal(), extpdf.expectedEvents(ROOT.RooArgSet())
                    
                pdf.SetName("pdf_%s" % treename)
                norm.SetName("norm_%s" % treename)
                norm.setVal(dset.sumEntries()*options.lumi_factor)
                ## extpdf.SetName("geneator_%s" % treename)
                self.workspace_.rooImport(pdf)
                self.workspace_.rooImport(norm)
                
                tnorm = dset.sumEntries()*options.lumi_factor
                print tnorm, norm.getVal()
                ntoys = options.n_toys

                for toy in range(ntoys):
                    data = pdf.generate(ROOT.RooArgSet(roobs),ROOT.gRandom.Poisson(tnorm)) ## 
                    if options.binned_toys: data=data.binnedClone()
                    toyname = "toy_%s%s_%d" % (comp,cat,toy)
                    data.SetName(toyname)
                    data.SetTitle(toyname)
                    self.workspace_.rooImport(data)
                
                #### print treename
                #### tree = self.treeData( treename )
                #### treobs = ROOT.TTreeFormula(roobs.GetName(),roobs.GetTitle(),tree)
                #### trewei = ROOT.TTreeFormula(roowe.GetName(),roowe.GetTitle(),tree)
                #### 
                #### tree.Draw("1>>hsum(1,0,2)","weight","goff")
                #### nev  = tree.GetEntries()
                #### hsum = ROOT.gDirectory.Get("hsum")
                #### norm = hsum.Integral()
                #### 
                #### ntoys = int(nev/norm)
                #### print norm,ntoys,nev
                #### 
                #### if options.split_mc >= 0:
                ####     ntoys = options.split_mc
                #### 
                ### evlist = range(nev)
                ### random.shuffle(evlist)
                ### 
                ### toy = -1
                ### data = None
                ### maxwei = 0.
                ### for iev in xrange(tree.GetEntries()):
                ###     tree.GetEntry(iev)
                ###     wei = trewei.EvalInstance()
                ###     maxwei = max(wei,maxwei)
                ### 
                ### print "maximum weight : %f" % maxwei
                ###     
                ### nev = 0 
                ### discarded = []
                ### while toy < ntoys:
                ###     for jev in xrange(len(evlist)):
                ###         iev = evlist[jev]
                ###         nev += 1
                ###         if toy == -1 or data.sumEntries() >= norm:
                ###             toy += 1
                ###             print "\nfilling toy : %d" % toy
                ###             if data:
                ###                 data.Print("V")
                ###                 self.workspace_.rooImport(data)                                
                ###             toyname = "toy%s_%s_%d" % (comp,cat,toy)
                ###             data = ROOT.RooDataHist(toyname,toyname,ROOT.RooArgSet(roobs))
                ###             if toy != 0:
                ###                 break
                ### 
                ###         tree.GetEntry(iev)
                ###         wei = trewei.EvalInstance() / maxwei
                ###         if ROOT.gRandom.Uniform() > wei:
                ###             continue
                ###         else:
                ###             discarded.append(iev)
                ### 
                ###         print "%1.2f\r" % ( data.sumEntries()/ float(nev)),
                ###     
                ###         val = treobs.EvalInstance()
                ###         roobs.setVal(val)
                ###         data.add(ROOT.RooArgSet(roobs),1.)
                ###     
                ###     print len(evlist)
                ###     evlist = evlist[jev:]+discarded
                ###     if len(evlist) < 1:
                ###         break
                    
        self.saveWs(options)


    ## ------------------------------------------------------------------------------------------------------------
    def fitToys(self,options,args):
        
        fout = self.openOut(options)
            
        fitname = options.fit
        fit = options.fits[fitname]
        
        roobs = self.buildRooVar(*(self.getVar(options.observable)), recycle=True)
        roobs.setRange("fitRange",*options.fit_range)
        roobs.setRange("fullRange",roobs.getMin(),roobs.getMax())
        testRanges = []
        for itest in xrange(len(options.test_ranges)/2):
            rname = "testRange_%1.0f_%1.0f" % ( options.test_ranges[2*itest],options.test_ranges[2*itest+1] )
            print rname, options.test_ranges[2*itest:2*itest+2]
            roobs.setRange( rname, *options.test_ranges[2*itest:2*itest+2] )
            testRanges.append( (rname,options.test_ranges[2*itest:2*itest+2]) )
        
        roowe = self.buildRooVar("weight",[])
        
        fitops = ( ROOT.RooFit.PrintLevel(-1),ROOT.RooFit.Warnings(False),ROOT.RooFit.NumCPU(4),ROOT.RooFit.Minimizer("Minuit2") )

        for comp,model in zip(options.components,options.models):
            if comp != "":
                comp = "%s_" % comp
            for cat in fit["categories"]:
                pdf = self.buildPdf(model,"%s%s" % (comp,cat), roobs )
                
                biases = {}
                for testRange in testRanges:
                    rname = testRange[0]
                    ntp = ROOT.TNtuple("tree_bias_%s%s_%s_%s" % (comp,cat,model,rname),"tree_bias_%s%s_%s_%s" % (comp,cat,model,rname),"toy:truth:fit:minos:errhe:errp:errm:bias" )
                    biases[rname] = ntp
                    self.store_[ntp.GetName()] = ntp
                    
                ## generator = self.rooPdf("geneator_mctruth_%s%s_%s" % (comp,fitname,cat))
                generator = self.rooPdf("pdf_mctruth_%s%s_%s" % (comp,fitname,cat))
                print generator
                gnorm     = self.buildRooVar("norm_mctruth_%s%s_%s" % (comp,fitname,cat), [], recycle=True)
                gnorm.Print()
                
                trueNorms = {}
                pobs  = generator.getDependents(ROOT.RooArgSet(roobs))[roobs.GetName()]
                pobs.setRange("fullRange",roobs.getBinning("fullRange").lowBound(),roobs.getBinning("fullRange").highBound())
                renorm = generator.createIntegral(ROOT.RooArgSet(pobs),"").getVal() / gnorm.getVal() ## / generator.expectedEvents(ROOT.RooArgSet(pobs))
                ## renorm = 1. / gnorm.getVal() ## / generator.expectedEvents(ROOT.RooArgSet(pobs))
                for test in testRanges:
                    testRange,testLim = test
                    pobs.setRange(testRange,roobs.getBinning(testRange).lowBound(),roobs.getBinning(testRange).highBound())
                    trueNorms[testRange] = generator.createIntegral(ROOT.RooArgSet(pobs),testRange).getVal()/renorm
                print trueNorms
                
                for toy in xrange(options.first_toy,options.first_toy+options.n_toys):
                    toyname = "toy_%s%s_%d" % (comp,cat,toy)
                    dset = self.rooData(toyname)
                    pdft = pdf.Clone()
                    
                    if options.plot_toys_fits:
                        frame = roobs.frame()
                        pdff = pdf.Clone()
                        pdff.fitTo(dset,ROOT.RooFit.Range("fullRange"),*fitops) ## ,ROOT.RooFit.PrintLevel(3),ROOT.RooFit.Verbose(True))                        
                        pdff.plotOn(frame,ROOT.RooFit.LineColor(ROOT.kGreen),ROOT.RooFit.Range("fullRange"))
                     
                    pdft.fitTo(dset,ROOT.RooFit.Range("fitRange"),*fitops)
                    
                        
                    if options.plot_toys_fits:
                        dset.plotOn(frame)
                        pdf.plotOn(frame,ROOT.RooFit.LineColor(ROOT.kRed))
                        pdft.plotOn(frame)
                        
                        canv = ROOT.TCanvas("fit_%s" % toyname,"fit_%s" % toyname)
                        canv.SetLogy()
                        canv.SetLogx()
                        frame.Draw()
                        self.keep( canv )
                    
                    for test in testRanges:
                        testRange,testLim = test
                        iname = "%s_%s_%s" % (toyname, model, testRange)

                        roonorm = ROOT.RooRealVar("norm_%s" % iname, "norm_%s" % iname, 0.)
                        roonorm.setConstant(False)
                        roonorm.setRange(0.,1.e+7)

                        integral = pdft.createIntegral(ROOT.RooArgSet(roobs),ROOT.RooArgSet(roobs),testRange)
                        nomnorm = integral.getVal()*dset.sumEntries()
                        roonorm.setVal(nomnorm)
                        truenorm = trueNorms[testRange] ## *dset.sumEntries()
                        print roonorm.getVal(), truenorm
                        epdf = ROOT.RooExtendPdf(iname,iname,pdf,roonorm,testRange)
                        
                        if options.exclude_test_range:
                            edset = dset.reduce("%s< %f || %s >%f" % ( roobs.GetName(), testLim[0], roobs.GetName(), testLim[1] ))
                        else:
                            edset = dset
                        nll = epdf.createNLL(edset,ROOT.RooFit.Extended())

                        minim = ROOT.RooMinimizer(nll)
                        minim.setPrintLevel(-1)
                        minim.setStrategy(0)
                        migrad = minim.migrad()
                                                
                        ## print migrad
                        if migrad != 0:
                            minim.setStrategy(0)
                            migrad = minim.migrad()
                            if migrad != 0:
                                continue
                        
                        nomnorm = roonorm.getVal()
                        
                        ## print truenorm, nomnorm, roonorm.getVal(), roonorm.getErrorHi(), roonorm.getErrorLo()
                        
                        minim.hesse()
                        ### print truenorm, nomnorm, roonorm.getVal(), roonorm.getErrorHi(), roonorm.getErrorLo()
                        hesseerr = roonorm.getError()
                        fiterrh = roonorm.getErrorHi()
                        fiterrl = roonorm.getErrorLo()
                        minos = minim.minos(ROOT.RooArgSet(roonorm))
                        if minos == 0:
                            ### print truenorm, nomnorm, roonorm.getVal(), roonorm.getErrorHi(), roonorm.getErrorLo()
                            if roonorm.getErrorHi() != 0.:
                                fiterrh = roonorm.getErrorHi()
                            if roonorm.getErrorLo() != 0.:
                                fiterrl = roonorm.getErrorLo()
                        
                        ### ### ### print "c"
                        ### fitval  = roonorm.getVal()
                        ### fiterrh = abs(roonorm.getErrorHi()/3.)
                        ### fiterrl = abs(roonorm.getErrorLo()/3.)
                        ### pll = nll.createProfile(ROOT.RooArgSet(roonorm))
                        ### minll = pll.getVal()
                        ### if fiterrl < fitval:
                        ###     roonorm.setVal(fitval-fiterrl)
                        ### else:
                        ###     roonorm.setVal(0.1)
                        ###     fiterrl = fitval - 0.1
                        ### nllm =  pll.getVal()
                        ### roonorm.setVal(fitval+fiterrh)
                        ### nllp =  pll.getVal()
                        ### 
                        ### ## print fiterrh, fiterrl, minll, nllm, nllp
                        ### 
                        ### if nllm-minll < 0. or nllp-minll < 0.: continue
                        ### fiterrh = fiterrh / sqrt(2.*(nllp-minll)) 
                        ### fiterrl = fiterrl / sqrt(2.*(nllm-minll))
                        ### 
                        ### ## y = a x^2
                        ### ## a = y/x^2
                        ### ## 1 = a*xe^2
                        ### ## xe = 1/sqrt(a) = x / sqrt(y)
                        
                        ### fiterrh = roonorm.getErrorHi()
                        ### fiterrl = roonorm.getErrorLo()
                        ## print truenorm, nomnorm, roonorm.getVal(), fiterrl, fiterrh
                        
                        errh = fiterrh if fiterrh != 0. else hesseerr
                        errl = fiterrl if fiterrl != 0. else hesseerr
                        if nomnorm > truenorm:                            
                            bias = (nomnorm-truenorm)/abs(errl)
                        else:
                            bias = (nomnorm-truenorm)/abs(errh)

                        biases[testRange].Fill( toy,truenorm, nomnorm,  minos, hesseerr, fiterrh, fiterrl, bias )
                    
                    self.autosave(True)
                        
        self.saveWs(options,fout)

    ## ------------------------------------------------------------------------------------------------------------
    def analyzeBias(self,options,args):
        
        summary = {}
        
        ROOT.gStyle.SetOptStat(1111)
        ROOT.gStyle.SetOptFit(1)
        
        for fname,label in zip(options.bias_files,options.bias_labels):
            fin = self.open(fname)
            for key in ROOT.TIter(fin.GetListOfKeys()):
                name = key.GetName()
                if name.startswith("tree_bias"):
                    toks = name.split("_",5)[2:]                    
                    comp,cat,model,rng = toks
                    tree = key.ReadObj()
                    toks.append(label)
                    
                    nlabel = "_".join(toks)

                    tree.Draw("bias>>h_bias_%s(501,-5.005,5.005)" % nlabel )
                    hb = ROOT.gDirectory.Get("h_bias_%s" % ("_".join(toks)))
                    hb.Fit("gaus","L+Q")
                    
                    canv = ROOT.TCanvas(nlabel,nlabel)
                    canv.cd()
                    hb.Draw()
                    
                    self.keep( [canv,hb] )
                    self.autosave(True)
                    
                    gaus = hb.GetListOfFunctions().At(0)
                    prb = array.array('d',[0.5])
                    med = array.array('d',[0.])
                    hb.GetQuantiles(len(prb),med,prb)
                    
                    tree.Draw("abs(bias)>>h_coverage_%s(501,0,5.01)" % ("_".join(toks)) )
                    hc = ROOT.gDirectory.Get("h_coverage_%s" % nlabel )
                    
                    prb = array.array('d',[0.683])
                    qtl = array.array('d',[0.])
                    hc.GetQuantiles(len(prb),qtl,prb)
                                        
                    summary[nlabel] = [ gaus.GetParameter(1), gaus.GetParError(1), gaus.GetParameter(2), gaus.GetParError(2),
                                        med[0], qtl[0] ]
                
        
        keys = sorted(summary.keys())
        maxl = 0
        for key in keys:
            maxl = max(len(key),maxl)
        summarystr = ""
        for key in keys:
            val = summary[key]
            summarystr += ("%s, " % key).ljust(maxl+3)
            for v in val: 
                summarystr += ("%1.3g," %v).rjust(9)
            summarystr += "\n"
        print summarystr
        summaryf = open("%s/README.txt" % options.outdir,"w+")
        summaryf.write(summarystr)
        summaryf.close()
        
        
    ## ------------------------------------------------------------------------------------------------------------
    def buildPdf(self,model,name,xvar,order=0):
        
        pdf = None
        if model == "dijet":
            pname = "dijet_%s" % name
            linc = self.buildRooVar("%s_lin" % pname,[], importToWs=False)
            logc = self.buildRooVar("%s_log" % pname,[], importToWs=False)
            linc.setVal(4.)
            logc.setVal(-10.)
            
            self.pdfPars_.add(linc)
            self.pdfPars_.add(logc)
            
            roolist = ROOT.RooArgList( xvar, linc, logc )
            pdf = ROOT.RooGenericPdf( pname, pname, "pow(@0,@1+@2*log(@0))", roolist )
            ## pdf = ROOT.RooGenericPdf( pname, pname, "pow(@0,@1)", roolist )
            
            self.keep( [pdf,linc,logc] )

        return pdf
      
                
# -----------------------------------------------------------------------------------------------------------
# actual main
if __name__ == "__main__":
    app = BiasApp()
    app.run()