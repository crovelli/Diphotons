#include <iostream>

#include <TROOT.h>
#include <TFile.h>
#include <TSystem.h>
#include "TTree.h"

#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/EDAnalyzer.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Utilities/interface/InputTag.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Framework/interface/ESHandle.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/ServiceRegistry/interface/Service.h"
#include "CommonTools/UtilAlgos/interface/TFileService.h"
#include "DataFormats/Common/interface/Handle.h"

#include "DataFormats/EcalDetId/interface/EBDetId.h"
#include "DataFormats/EcalDetId/interface/EEDetId.h"
#include "DataFormats/EcalRecHit/interface/EcalRecHitCollections.h"
#include "Geometry/CaloTopology/interface/CaloTopology.h"
#include "Geometry/CaloEventSetup/interface/CaloTopologyRecord.h"
#include "RecoCaloTools/Navigation/interface/CaloNavigator.h"
#include "RecoEcal/EgammaCoreTools/interface/EcalClusterLazyTools.h"
#include "Geometry/Records/interface/CaloGeometryRecord.h"

#include "RecoLocalCalo/EcalDeadChannelRecoveryAlgos/interface/EcalDeadChannelRecoveryAlgos.h" 

#include "flashgg/MicroAODFormats/interface/Photon.h"


using namespace std;
using namespace edm;

// per event tree
struct eventTree_struc_ {  

  int nPho;
  int nMatchedPho;
};

// per photon tree
struct phoTree_struc_ {    

  int run;
  int event;
  int nvertex;

  float pt;
  float eta;
  float phi;
  int isEBEtaGap;
  int isEBPhiGap;
  int isEERingGap;
  int isEEDeeGap;
  int isEBEEGap;

  float scEta;
  float scPhi;

  float eMax;
  float e5x5;
  float energy;
  float energyInitial;
  float energyRegression;

  float e1x5;
  float e2x5;
  float sigmaIetaIeta;
  float r9;

  float hoe;
  float h1oe;
  float h2oe;
  float htoe;
  float ht1oe;
  float ht2oe;

  bool passEleVeto;
  bool hasPixelSeed;

  float trackIso;
  float ecalIso;
  float hcalIso;
  float chHadIso;
  float nHadIso;
  float photonIso;
  float rho;

  float sigmaIetaIetaNoZS;
  float e5x5NoZS;
  float r9NoZS;

  float trueEnergy;
  float truePt;
  float trueEta;
  float truePhi;
  float minDR;

  float amplit[25];
  int ieta[25];
  int iphi[25];
  int ix[25];
  int iy[25];
  int iz[25];
  int kSaturated[25];
  int kLeRecovered[25];
  float amplitRecovered[25];

  // da DataFormats/EgammaCandidates/interface/Photon.h, ma da capire come spacchettare
  // const EnergyCorrections & energyCorrections() const { return eCorrections_ ; }
};

class SinglePhoAnalyzer : public edm::EDAnalyzer {

public:
  explicit SinglePhoAnalyzer(const edm::ParameterSet&);
  ~SinglePhoAnalyzer();
  
private:

  edm::Service<TFileService> fs_;
  
  virtual void beginJob() override;
  virtual void analyze(const edm::Event&, const edm::EventSetup&) override;
  virtual void endJob() override;

  void initEvtTreeStructure();
  void initPhoTreeStructure();

  // declarations: trees per event and photon
  TTree *eventTree;
  TTree *phoTree;  
  eventTree_struc_ treeEv_;
  phoTree_struc_ tree_;  

  // saturation
  EcalDeadChannelRecoveryAlgos<EBDetId> ebDeadChannelCorrector;
  EcalDeadChannelRecoveryAlgos<EEDetId> eeDeadChannelCorrector;

  // collections
  edm::EDGetTokenT<edm::View<flashgg::Photon> > photonToken_;
  edm::EDGetTokenT<View<reco::GenParticle> > genParticleToken_;
  edm::EDGetTokenT<EcalRecHitCollection> ecalHitEBToken_;
  edm::EDGetTokenT<EcalRecHitCollection> ecalHitEEToken_;
  edm::EDGetTokenT<edm::View<reco::Vertex> > vertexToken_;
};

SinglePhoAnalyzer::SinglePhoAnalyzer(const edm::ParameterSet& iConfig): 
  photonToken_(consumes<View<flashgg::Photon> >(iConfig.getUntrackedParameter<InputTag> ("PhotonTag", InputTag("flashggPhotons")))), 
  genParticleToken_(consumes<View<reco::GenParticle> >(iConfig.getUntrackedParameter<InputTag> ("GenParticleTag", InputTag("prunedGenParticles")))),
  ecalHitEBToken_(consumes<EcalRecHitCollection>(iConfig.getParameter<edm::InputTag>("reducedBarrelRecHitCollection"))),
  ecalHitEEToken_(consumes<EcalRecHitCollection>(iConfig.getParameter<edm::InputTag>("reducedEndcapRecHitCollection"))),
  vertexToken_(consumes<View<reco::Vertex> >(iConfig.getUntrackedParameter<InputTag> ("VertexTag", InputTag("offlineSlimmedPrimaryVertices"))))
{
}

SinglePhoAnalyzer::~SinglePhoAnalyzer() { } 

void SinglePhoAnalyzer::analyze(const edm::Event& iEvent, const edm::EventSetup& iSetup) {

  // access edm objects
  Handle<View<flashgg::Photon> > objs_pho;
  iEvent.getByToken(photonToken_,objs_pho);
  const PtrVector<flashgg::Photon>& photonPointers = objs_pho->ptrVector();

  Handle<View<reco::GenParticle> > objs_gens;
  iEvent.getByToken(genParticleToken_,objs_gens);
  const PtrVector<reco::GenParticle>& genPointers = objs_gens->ptrVector();

  Handle<double> objs_rho;
  iEvent.getByLabel("fixedGridRhoAll",objs_rho); 
  const double rhoFixedGrd = *(objs_rho.product());

  Handle<View<reco::Vertex> > primaryVertices;
  iEvent.getByToken(vertexToken_,primaryVertices);
  const PtrVector<reco::Vertex>& pvPointers = primaryVertices->ptrVector();

  Handle< EcalRecHitCollection > EcalBarrelRecHits;
  iEvent.getByToken(ecalHitEBToken_, EcalBarrelRecHits); 
  Handle< EcalRecHitCollection > EcalEndcapRecHits;
  iEvent.getByToken(ecalHitEEToken_, EcalEndcapRecHits); 

  const CaloSubdetectorTopology* theSubdetTopologyEB_;
  const CaloSubdetectorTopology* theSubdetTopologyEE_;
  edm::ESHandle<CaloTopology> theCaloTopology;
  iSetup.get<CaloTopologyRecord>().get(theCaloTopology);
  theSubdetTopologyEB_ = theCaloTopology->getSubdetectorTopology(DetId::Ecal,EcalBarrel);
  theSubdetTopologyEE_ = theCaloTopology->getSubdetectorTopology(DetId::Ecal,EcalEndcap);

  // to recompute not-zero-suppressed cluster shapes
  noZS::EcalClusterLazyTools *lazyToolnoZS = new noZS::EcalClusterLazyTools(iEvent, iSetup, ecalHitEBToken_, ecalHitEEToken_);

  // real analysis
  int allGamma = 0;
  int matchedGamma = 0;

  
  // event tree re-initialization
  initEvtTreeStructure();

  // loop over photons
  for( size_t ipho = 0; ipho < photonPointers.size(); ipho++ ) {

    Ptr<flashgg::Photon> g1 = photonPointers[ipho];

    // mninimal selection to speed up: photon eta and pT cuts
    float gammaPt    = g1->pt();
    float gammaScEta = (g1->superCluster())->eta();
    if (gammaPt<30) continue;
    if (fabs(gammaScEta)>2.5) continue;
    if (fabs(gammaScEta)>1.4442 && fabs(gammaScEta)<1.566) continue;

    // photon tree re-initialization
    initPhoTreeStructure();

    // filling the photon tree with basic infos
    tree_.run = iEvent.id().run(); 
    tree_.event = iEvent.id().event(); 
    tree_.nvertex = pvPointers.size();

    tree_.pt =g1->pt();
    tree_.eta=g1->eta();
    tree_.phi=g1->phi();
    tree_.isEBEtaGap=g1->isEBEtaGap();
    tree_.isEBPhiGap=g1->isEBPhiGap();
    tree_.isEERingGap=g1->isEERingGap();
    tree_.isEEDeeGap=g1->isEEDeeGap();
    tree_.isEBEEGap=g1->isEBEEGap();

    tree_.scEta = (g1->superCluster())->eta();
    tree_.scPhi = (g1->superCluster())->phi();

    tree_.eMax=g1->maxEnergyXtal();
    tree_.e5x5=g1->e5x5();
    tree_.energy=g1->energy();
    tree_.energyInitial=g1->getEnergyAtStep("initial");
    tree_.energyRegression=g1->getEnergyAtStep("regression");

    tree_.e1x5=g1->e1x5();
    tree_.e2x5=g1->e2x5();
    tree_.sigmaIetaIeta = g1->sigmaIetaIeta();
    tree_.r9 = g1->r9();

    tree_.hoe   = g1->hadronicOverEm();
    tree_.h1oe  = g1->hadronicDepth1OverEm();
    tree_.h2oe  = g1->hadronicDepth2OverEm();
    tree_.htoe  = g1->hadTowOverEm();
    tree_.ht1oe = g1->hadTowDepth1OverEm();
    tree_.ht2oe = g1->hadTowDepth2OverEm();

    tree_.passEleVeto  = g1->passElectronVeto();
    tree_.hasPixelSeed = g1->hasPixelSeed();

    // DeltaR=0.4 (di sicuro per detector-based, credo anche per PF-based)
    tree_.trackIso  = g1->trackIso();
    tree_.ecalIso   = g1->ecalIso();
    tree_.hcalIso   = g1->hcalIso();
    tree_.chHadIso  = g1->chargedHadronIso();
    tree_.nHadIso   = g1->neutralHadronIso();
    tree_.photonIso = g1->photonIso();
    tree_.rho       = rhoFixedGrd;

    // not zero-suppressed quantities 
    std::vector<float> vCovnoZS = lazyToolnoZS->localCovariances(*(g1->superCluster()->seed())) ;
    float sieienoZS;
    if (!isnan(vCovnoZS[0])) 
      sieienoZS = sqrt (vCovnoZS[0]);       // chiara: sometimes is 999.9 (probably missing rechits)
    else sieienoZS = 100.;

    float e5x5noZS = lazyToolnoZS->e5x5(*(g1->superCluster()->seed()));
    float r9noZS   = lazyToolnoZS->e3x3(*(g1->superCluster()->seed())) / g1->superCluster()->rawEnergy();

    tree_.sigmaIetaIetaNoZS = sieienoZS;
    tree_.e5x5NoZS = e5x5noZS;
    tree_.r9NoZS = r9noZS;

    // we save all photons, and we decide using these flags if they are true or not
    float matchedEne = -999.;
    float matchedPt  = -999.;
    float matchedEta = -999.;
    float matchedPhi = -999.;
    float minDR = 999.;

    for( unsigned int genLoop =0 ; genLoop < genPointers.size(); genLoop++) {

      Ptr<reco::GenParticle> gen = genPointers[genLoop];

      if ( gen->pdgId() != 22 ) continue;

      bool genOk = false;      
      
      // chiara: when running on graviton samples
      if( gen->status() == 1 && (gen->mother())->pdgId()==5100039 ) genOk = true;

      // chiara: when running on g+jets samples 
      // if ( gen->status() == 3 ) genOk = true;    
      // else if ( gen->status() == 1 ) {
      // int mpdgId = gen->mother(0)->pdgId();
      // int mpdgSt = gen->mother(0)->status();
      // if (mpdgId==22 && (mpdgSt==22 || mpdgSt==23 || mpdgSt==3)) genOk = true;
      // }              

      // hardcoded: dR<0.01 & pT/pTtrue>0.5
      if (genOk) {
	float dR = deltaR(gen->eta(),gen->phi(),g1->eta(),g1->phi());
	if ( dR<minDR ) {
	  minDR = dR;
	  if ( dR<0.01 ) {
	    float genPt  = fabs(gen->energy()*sin(gen->theta()));
	    float recoPt = g1->pt(); 
	    if ((recoPt/genPt)>0.5) {
	      matchedEne = gen->energy();
	      matchedPt  = fabs(gen->energy()*sin(gen->theta()));
	      matchedEta = gen->eta();
	      matchedPhi = gen->phi();
	      break;
	    }
	  }
	}
      }
    } // loop over gen photons

    tree_.trueEnergy = matchedEne;
    tree_.truePt = matchedPt;
    tree_.trueEta = matchedEta;
    tree_.truePhi = matchedPhi;
    tree_.minDR = minDR;

    
    // extra info on rechits for xtals in the 5x5 matrix around the seed
    DetId seedDetId = ( (g1->superCluster())->seed() )->seed();
    
    if(seedDetId.subdetId()==EcalEndcap) {
      
      int iNeigh=0; 
      
      CaloNavigator<DetId> cursorE = CaloNavigator<DetId>(seedDetId, theSubdetTopologyEE_ );

      for(int ix=-2; ix<3; ++ix) {
	for(int iy=-2; iy<3; ++iy) {
	  cursorE.home();
	  cursorE.offsetBy( ix, iy );
	  DetId cryId = cursorE.pos();

	  if(cryId.subdetId()!=EcalEndcap) { 
	    tree_.amplit[iNeigh] = -5000.;
	    tree_.ieta[iNeigh] = -5000; 
	    tree_.iphi[iNeigh] = -5000;
	    tree_.ix[iNeigh] = -5000; 
	    tree_.iy[iNeigh] = -5000; 
	    tree_.iz[iNeigh] = -5000; 
	    tree_.kSaturated[iNeigh] = -5000;
	    tree_.kLeRecovered[iNeigh] = -5000;
	    tree_.amplitRecovered[iNeigh] = -5000.;
	    iNeigh++;
	    continue;  
	  }

	  EcalRecHitCollection::const_iterator itneigh = EcalEndcapRecHits->find( cryId );

	  if( itneigh != EcalEndcapRecHits->end() ) {
	    tree_.amplit[iNeigh] = itneigh->energy();
	    tree_.ieta[iNeigh] = -999; 
	    tree_.iphi[iNeigh] = -999; 
	    tree_.ix[iNeigh] = ((EEDetId)itneigh->detid()).ix();
	    tree_.iy[iNeigh] = ((EEDetId)itneigh->detid()).iy();
	    tree_.iz[iNeigh] = ((EEDetId)itneigh->detid()).zside();
	    tree_.kSaturated[iNeigh] = itneigh->checkFlag(EcalRecHit::kSaturated);      
	    tree_.kLeRecovered[iNeigh] = itneigh->checkFlag(EcalRecHit::kLeadingEdgeRecovered);      

	    // extra saturation studies
	    if (tree_.kSaturated[iNeigh] || tree_.kLeRecovered[iNeigh]) {
	      eeDeadChannelCorrector.setCaloTopology(theCaloTopology.product());
	      bool AcceptRecHit=true;
	      EcalRecHit hit = eeDeadChannelCorrector.correct( (EEDetId)itneigh->detid(), *EcalEndcapRecHits, "NeuralNetworks", 8, &AcceptRecHit);
	      tree_.amplitRecovered[iNeigh] = hit.energy();
	    } else {
	      tree_.amplitRecovered[iNeigh] = -999.;	      
	    }

	  } else {
	    tree_.amplit[iNeigh] = -2000.;
	    tree_.ieta[iNeigh] = -2000; 
	    tree_.iphi[iNeigh] = -2000;
	    tree_.ix[iNeigh] = -2000; 
	    tree_.iy[iNeigh] = -2000; 
	    tree_.iz[iNeigh] = -2000; 
	    tree_.kSaturated[iNeigh] = -2000;
	    tree_.kLeRecovered[iNeigh] = -2000;
	    tree_.amplitRecovered[iNeigh] = -2000.;
	  }
	  
	  iNeigh++;
	}
      }
      if (iNeigh!=25) cout << "problem: not 25 crystals!  ==> " << iNeigh << endl;
      
    } else if (seedDetId.subdetId()==EcalBarrel) {
      
      int iNeigh=0; 

      CaloNavigator<DetId> cursorE = CaloNavigator<DetId>(seedDetId, theSubdetTopologyEB_ );

      for(int ix=-2; ix<3; ++ix) {
	for(int iy=-2; iy<3; ++iy) {
	  cursorE.home();
	  cursorE.offsetBy( ix, iy );
	  DetId cryId = cursorE.pos();

	  if(cryId.subdetId()!=EcalBarrel) { 
	    tree_.amplit[iNeigh] = -5000.;
	    tree_.ieta[iNeigh] = -5000; 
	    tree_.iphi[iNeigh] = -5000;
	    tree_.ix[iNeigh] = -5000; 
	    tree_.iy[iNeigh] = -5000; 
	    tree_.iz[iNeigh] = -5000; 
	    tree_.kSaturated[iNeigh] = -5000;
	    tree_.kLeRecovered[iNeigh] = -5000;
	    tree_.amplitRecovered[iNeigh] = -5000.;
	    iNeigh++;
	    continue;  
	  }
	  
	  EcalRecHitCollection::const_iterator itneigh = EcalBarrelRecHits->find( cryId );

	  if( itneigh != EcalBarrelRecHits->end() ) { 
	    tree_.amplit[iNeigh] = itneigh->energy();
	    tree_.ieta[iNeigh] = ((EBDetId)itneigh->detid()).ieta();
	    tree_.iphi[iNeigh] = ((EBDetId)itneigh->detid()).iphi();
	    tree_.ix[iNeigh] = -999;
	    tree_.iy[iNeigh] = -999;
	    tree_.iz[iNeigh] = -999;
	    tree_.kSaturated[iNeigh] = itneigh->checkFlag(EcalRecHit::kSaturated);      
	    tree_.kLeRecovered[iNeigh] = itneigh->checkFlag(EcalRecHit::kLeadingEdgeRecovered);      
	    // extra saturation studies
	    if (tree_.kSaturated[iNeigh] || tree_.kLeRecovered[iNeigh]) {
	      ebDeadChannelCorrector.setCaloTopology(theCaloTopology.product());
	      bool AcceptRecHit=true;
	      EcalRecHit hit = ebDeadChannelCorrector.correct( (EBDetId)itneigh->detid(), *EcalBarrelRecHits, "NeuralNetworks", 8, &AcceptRecHit);
	      tree_.amplitRecovered[iNeigh] = hit.energy();
	    } else {
	      tree_.amplitRecovered[iNeigh] = -999.;
	    }

	  } else {
	    tree_.amplit[iNeigh] = -2000.;
	    tree_.ieta[iNeigh] = -2000; 
	    tree_.iphi[iNeigh] = -2000;
	    tree_.ix[iNeigh] = -2000; 
	    tree_.iy[iNeigh] = -2000; 
	    tree_.iz[iNeigh] = -2000; 
	    tree_.kSaturated[iNeigh] = -2000;
	    tree_.kLeRecovered[iNeigh] = -2000;
	    tree_.amplitRecovered[iNeigh] = -2000.;
	  }

	  iNeigh++;
	}
      }
      if (iNeigh!=25) cout << "problem: not 25 crystals!  ==> " << iNeigh << endl;

      // if (tree_.kSaturated[12] || tree_.kLeRecovered[12]) {  
      // std::cout << "chiara: check from my code ==> " << std::endl;
      // std::cout << tree_.amplit[6]  << " " << tree_.amplit[7]  << " " << tree_.amplit[8]  << " " 
      // << tree_.amplit[11] << " " << tree_.amplit[12] << " " << tree_.amplit[13] << " " 
      // << tree_.amplit[16] << " " << tree_.amplit[17] << " " << tree_.amplit[18] << endl; 
      // }

    }

    // to count the number of reco photons and reco matching gen ones
    allGamma++;
    if (matchedEne>-1) matchedGamma++;

    phoTree->Fill();

  } // loop over reco photons

  // filling the tree with per-event infos
  treeEv_.nPho = allGamma;
  treeEv_.nMatchedPho = matchedGamma;
  eventTree->Fill();

  delete lazyToolnoZS;
}

void SinglePhoAnalyzer::beginJob() {

  eventTree = fs_->make<TTree>("eventTree","per-event tree");
  phoTree   = fs_->make<TTree>("singlePhotons","single photon tree");  
  
  // tree per event
  TString treeEvent = "nPho/I:nMatchedPho/I";
  eventTree->Branch("event",&(treeEv_.nPho),treeEvent); 

  // tree per photon
  TString treeKine = "pt/F:eta/F:phi/F:isEBEtaGap/I:isEBPhiGap/I:isEERingGap/I:isEEDeeGap/I:isEBEEGap/I";
  TString treeSc = "scEta/F:scPhi/F";
  TString treeEne = "eMax/F:e5x5/F:energy/F:energyInitial/F:energyRegression/F";
  TString treeID = "e1x5/F:e2x5/F:sigmaIetaIeta/F:r9/F:hoe/F:h1oe/F:h2oe/F:htoe/F:ht1oe/F:ht2oe/F:passEleVeto/B:hasPixelSeed/B";
  TString treeIso = "trackIso/F:ecalIso/F:hcalIso/F:chHadIso/F:nHadIso/F:photonIso/F:rho/F";
  TString treeIDnoZS = "sieienoZS/F:e5x5noZS/F:r9noZS/F";
  TString treeTrue = "trueEnergy/F:truePt/F:trueEta/F:truePhi/F:minDR/F";
  TString tree5x5 = "amplit[25]/F:ieta[25]/I:iphi[25]/I:ix[25]/I:iy[25]/I:iz[25]/I:kSaturated[25]/I:kLeRecovered[25]/I:amplitRecovered[25]/F";
  TString treeEve = "run/I:event/I:nvertex/I";
  phoTree->Branch("kinematics",&(tree_.pt),treeKine);
  phoTree->Branch("supercluster",&(tree_.scEta),treeSc);
  phoTree->Branch("energy",&(tree_.eMax),treeEne);
  phoTree->Branch("identification",&(tree_.e1x5),treeID);
  phoTree->Branch("isolation",&(tree_.trackIso),treeIso);
  phoTree->Branch("identificationNoZS",&(tree_.sigmaIetaIetaNoZS),treeIDnoZS);
  phoTree->Branch("mctruth",&(tree_.trueEnergy),treeTrue);
  phoTree->Branch("tree5x5",&(tree_.amplit),tree5x5);  
  phoTree->Branch("eventInfo",&(tree_.run),treeEve);
}

void SinglePhoAnalyzer::endJob() { 

}

void SinglePhoAnalyzer::initPhoTreeStructure() {

  tree_.run=-500; 
  tree_.event=-500; 
  tree_.nvertex=-500;
  tree_.pt=-500.;
  tree_.eta=-500.;
  tree_.phi=-500.;
  tree_.isEBEtaGap=-500;
  tree_.isEBPhiGap=-500;
  tree_.isEERingGap=-500;
  tree_.isEEDeeGap=-500;
  tree_.isEBEEGap=-500;
  tree_.scEta=-500.;
  tree_.scPhi=-500.;
  tree_.eMax=-500.;
  tree_.e5x5=-500.;
  tree_.energy=-500.;
  tree_.energyInitial=-500.;
  tree_.energyRegression=-500.;
  tree_.e1x5=-500.;
  tree_.e2x5=-500.;
  tree_.sigmaIetaIeta=-500.; 
  tree_.r9=-500.; 
  tree_.hoe=-500.; 
  tree_.h1oe=-500.; 
  tree_.h2oe=-500.; 
  tree_.htoe=-500.; 
  tree_.ht1oe=-500.; 
  tree_.ht2oe=-500.; 
  tree_.passEleVeto=-500;
  tree_.hasPixelSeed=-500;
  tree_.trackIso=-500.;
  tree_.ecalIso=-500.;
  tree_.hcalIso=-500.;
  tree_.chHadIso=-500.;
  tree_.nHadIso=-500.;
  tree_.photonIso=-500.;
  tree_.rho=-500.;
  tree_.sigmaIetaIetaNoZS=-500.;
  tree_.e5x5NoZS=-500.;
  tree_.r9NoZS=-500.;
  tree_.trueEnergy=-500.;
  tree_.truePt=-500.;
  tree_.trueEta=-500.;
  tree_.truePhi=-500.;
  tree_.minDR=-500.;
  for (uint iNeigh=0; iNeigh<25; iNeigh++) {
    tree_.amplit[iNeigh]=-500.;
    tree_.kSaturated[iNeigh]=-500;
    tree_.kLeRecovered[iNeigh]=-500;
    tree_.amplitRecovered[iNeigh]=-500.;
    tree_.ieta[iNeigh]=-500;
    tree_.iphi[iNeigh]=-500;
    tree_.ix[iNeigh]=-500;
    tree_.iy[iNeigh]=-500;
    tree_.iz[iNeigh]=-500;
  }
}

void SinglePhoAnalyzer::initEvtTreeStructure() {

  treeEv_.nPho=-500;
  treeEv_.nMatchedPho=-500;
}

DEFINE_FWK_MODULE(SinglePhoAnalyzer);