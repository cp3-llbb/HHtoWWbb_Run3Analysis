
from bamboo.plots import Plot, CutFlowReport
from bamboo.plots import EquidistantBinning as EqBin
from bamboo import treefunctions as op

import definitions as defs

from basePlotter import NanoBaseHHWWbb


class controlPlotter(NanoBaseHHWWbb):
    """"""

    def __init__(self, args):
        super(controlPlotter, self).__init__(args)
        self.channel = self.args.channel

    def definePlots(self, tree, noSel, sample=None, sampleCfg=None):
        plots = []
        yields = CutFlowReport("yields", printInLog=True, recursive=True)
        plots.append(yields)
        yields.add(noSel, 'No Selection')

        # Muons
        muon_conept = defs.muonConePt(tree.Muon)

        muons = op.sort(
            op.select(tree.Muon, lambda mu: defs.muonDef(mu)),
            lambda mu: -muon_conept[mu.idx]
        )

        fakeMuons = defs.muonFakeSel(muons)

        tightMuons = op.select(fakeMuons, lambda mu: defs.muonTightSel(mu))

        # Electrons
        electron_conept = defs.elConePt(tree.Electron)

        electrons = op.sort(
            op.select(tree.Electron, lambda el: defs.elDef(el)),
            lambda el: -electron_conept[el.idx]
        )
        # Cleaned Electrons
        clElectrons = defs.cleanElectrons(electrons, muons)

        # Fake Electrons
        fakeElectrons = defs.elFakeSel(clElectrons)

        tightElectrons = op.select(
            fakeElectrons, lambda el: defs.elTightSel(el))

        # AK4 Jets
        ak4JetsPreSel = op.sort(
            op.select(tree.Jet, lambda jet: defs.ak4jetDef(jet)), lambda jet: -jet.pt)

        # remove jets within cone of DR<0.4 of leading leptons at each channel

        if self.channel == 'SL':
            def cleaningWithRespectToLeadingLepton(DR):
                return lambda jet: op.multiSwitch(
                    (op.AND(op.rng_len(fakeElectrons) >= 1, op.rng_len(
                        fakeMuons) == 0), op.deltaR(jet.p4, fakeElectrons[0].p4) >= DR),
                    (op.AND(op.rng_len(fakeElectrons) == 0, op.rng_len(
                        fakeMuons) >= 1), op.deltaR(jet.p4, fakeMuons[0].p4) >= DR),
                    (op.AND(op.rng_len(fakeMuons) >= 1, op.rng_len(fakeElectrons) >= 1), op.switch(
                        electron_conept[0] >= muon_conept[0],
                        op.deltaR(jet.p4, fakeElectrons[0].p4) >= DR,
                        op.deltaR(jet.p4, fakeMuons[0].p4) >= DR)),
                    op.c_bool(True)
                )
            cleanAk4Jets = cleaningWithRespectToLeadingLepton(0.4)

        if self.channel == 'DL':
            def cleaningWithRespectToLeadingLeptons(DR):
                return lambda j: op.multiSwitch(
                    # Only electrons
                    (op.AND(op.rng_len(fakeElectrons) >= 2, op.rng_len(fakeMuons) == 0),
                     op.AND(op.deltaR(j.p4, fakeElectrons[0].p4) >= DR, op.deltaR(j.p4, fakeElectrons[1].p4) >= DR)),
                    # Only muons
                    (op.AND(op.rng_len(fakeElectrons) == 0, op.rng_len(fakeMuons) >= 2),
                     op.AND(op.deltaR(j.p4, fakeMuons[0].p4) >= DR, op.deltaR(j.p4, fakeMuons[1].p4) >= DR)),
                    # One electron + one muon
                    (op.AND(op.rng_len(fakeElectrons) == 1, op.rng_len(fakeMuons) == 1),
                     op.AND(op.deltaR(j.p4, fakeElectrons[0].p4) >= DR, op.deltaR(j.p4, fakeMuons[0].p4) >= DR)),
                    # At least one electron + at least one muon
                    (op.AND(op.rng_len(fakeElectrons) >= 1, op.rng_len(fakeMuons) >= 1),
                     op.switch(
                        # Electron is the leading lepton
                        electron_conept[0] > muon_conept[0],
                        op.switch(op.rng_len(fakeElectrons) == 1,
                                  op.AND(op.deltaR(j.p4, fakeElectrons[0].p4) >= DR, op.deltaR(
                                      j.p4, fakeMuons[0].p4) >= DR),
                                  op.switch(electron_conept[1] > muon_conept[0],
                                            op.AND(op.deltaR(j.p4, fakeElectrons[0].p4) >= DR, op.deltaR(
                                                j.p4, fakeElectrons[1].p4) >= DR),
                                            op.AND(op.deltaR(j.p4, fakeElectrons[0].p4) >= DR, op.deltaR(j.p4, fakeMuons[0].p4) >= DR))),
                        # Muon is the leading lepton
                        op.switch(op.rng_len(fakeMuons) == 1,
                                  op.AND(op.deltaR(j.p4, fakeMuons[0].p4) >= DR, op.deltaR(
                                      j.p4, fakeElectrons[0].p4) >= DR),
                                  op.switch(muon_conept[1] > electron_conept[0],
                                            op.AND(op.deltaR(j.p4, fakeMuons[0].p4) >= DR, op.deltaR(
                                                j.p4, fakeMuons[1].p4) >= DR),
                                            op.AND(op.deltaR(j.p4, fakeMuons[0].p4) >= DR, op.deltaR(j.p4, fakeElectrons[0].p4) >= DR))))),
                    op.c_bool(True)
                )
            cleanAk4Jets = cleaningWithRespectToLeadingLeptons(0.4)

        ak4Jets = op.select(ak4JetsPreSel, cleanAk4Jets)
        ak4JetsByBtagScore = op.sort(ak4Jets, lambda j: -j.btagDeepFlavB)

        # bTagging for ak4 jets
        def ak4BtagLooseSel(jet): return jet.btagDeepFlavB > 0.0494
        def ak4BtagSel(jet): return jet.btagDeepFlavB > 0.2770
        def ak4NoBtagSel(jet): return jet.btagDeepFlavB <= 0.2770

        ak4BJets = op.select(ak4Jets, ak4BtagSel)
        ak4BJetsLoose = op.select(ak4Jets, ak4BtagLooseSel)
        ak4LightJetsByPt = op.select(ak4Jets, ak4NoBtagSel)
        ak4LightJetsByBtagScore = op.sort(
            ak4LightJetsByPt, lambda jet: -jet.btagDeepFlavB)
        remainingJets = op.select(
            ak4LightJetsByPt, lambda jet: jet.idx != ak4LightJetsByBtagScore[0].idx)

        def makeJetPairs(jets): return op.combine(
            jets, N=2, pred=lambda j1, j2: j1.pt > j2.pt, samePred=lambda j1, j2: j1.idx != j2.idx)
        # --------------------------------------------- #
        bJetsByScore = ak4JetsByBtagScore[:op.min(op.rng_len(
            ak4JetsByBtagScore), op.static_cast("std::size_t", op.c_int(2)))]
        probableWJets = op.select(ak4Jets, lambda jet: op.NOT(
            op.rng_any(bJetsByScore, lambda bjet: jet.idx == bjet.idx)))
        wJetsByPt = probableWJets[:op.min(op.rng_len(
            probableWJets), op.static_cast("std::size_t", op.c_int(2)))]

        def passWMassCutSel(wjets): return op.switch(op.rng_len(wjets) == 2, op.abs(
            op.invariant_mass(wjets[0].p4, wjets[1].p4)-80.4) < op.c_float(15.0), op.c_bool(False))

        # AK8 Jets
        ak8JetsByPt = op.sort(tree.FatJet, lambda jet: -jet.pt)
        ak8JetsByDeepB = op.sort(tree.FatJet, lambda jet: -jet.btagDeepB)

        if self.channel == 'SL':
            ak8JetsPreSel = op.select(ak8JetsByDeepB, defs.ak8jetDef)
        if self.channel == 'DL':
            ak8JetsPreSel = op.select(ak8JetsByPt, defs.ak8jetDef)

        # Cleaning #
        if self.channel == 'SL':
            cleanAk8Jets = cleaningWithRespectToLeadingLepton(0.8)
        if self.channel == 'DL':
            cleanAk8Jets = cleaningWithRespectToLeadingLeptons(0.8)

        ak8Jets = op.select(ak8JetsPreSel, cleanAk8Jets)

        # 2018 DeepJet WP
        def subjetBtag(subjet): return subjet.btagDeepB > 0.4184

        def ak8Btag(fatjet): return op.OR(op.AND(fatjet.subJet1.pt >= 30, subjetBtag(fatjet.subJet1)),
                                          op.AND(fatjet.subJet2.pt >= 30, subjetBtag(fatjet.subJet2)))

        def ak8noBtag(fatjet): return op.NOT(op.OR(op.AND(fatjet.subJet1.pt >= 30, subjetBtag(fatjet.subJet1)),
                                                   op.AND(fatjet.subJet2.pt >= 30, subjetBtag(fatjet.subJet2))))

        def ak8Btag_bothSubJets(fatjet): return op.AND(op.AND(fatjet.subJet1.pt >= 30, subjetBtag(fatjet.subJet1)),
                                                       op.AND(fatjet.subJet2.pt >= 30, subjetBtag(fatjet.subJet2)))

        ak8BJets = op.select(ak8Jets, ak8Btag)
        ak8nonBJets = op.select(ak8Jets, ak8noBtag)
        # Ak4 Jet Collection cleaned from Ak8b #

        def cleanAk4FromAk8b(ak4j): return op.AND(op.rng_len(
            ak8BJets) > 0, op.deltaR(ak4j.p4, ak8BJets[0].p4) > 1.2)
        ak4JetsCleanedFromAk8b = op.select(ak4Jets, cleanAk4FromAk8b)

        # used as a BDT input for SemiBoosted category
        def btaggedSubJets(fjet): return op.switch(
            ak8Btag_bothSubJets(fjet), op.c_float(2.0), op.c_float(1.0))
        nMediumBTaggedSubJets = op.rng_sum(ak8BJets, btaggedSubJets)

        # Taus

        taus = defs.tauDef(tree.Tau)

        cleanedTaus = op.select(taus, lambda tau: op.AND(
            op.rng_any(fakeElectrons, lambda el: op.deltaR(
                el.p4, tau.p4) > 0.3),
            op.rng_any(fakeMuons, lambda mu: op.deltaR(mu.p4, tau.p4) > 0.3)
        ))

        ### Di-leptonic channel ###

        # has exactly two leptons
        # hasTwoL = noSel.refine('hasTwoL', cut=(
        #     op.OR(
        #         op.AND(op.rng_len(clElectrons) == 2, op.rng_len(muons) == 0,
        #                clElectrons[0].charge != clElectrons[1].charge, clElectrons[0].pt > 25., clElectrons[1].pt > 15.),
        #         op.AND(op.rng_len(muons) == 2, op.rng_len(clElectrons) == 0,
        #                muons[0].charge != muons[1].charge, muons[0].pt > 25., muons[1].pt > 15.),
        #         op.AND(op.rng_len(clElectrons) == 1, op.rng_len(muons) == 1,
        #                clElectrons[0].charge != muons[0].charge,
        #                op.switch(
        #             clElectrons[0].pt >= muons[0].pt,
        #             op.AND(clElectrons[0].pt > 25., muons[0].pt > 15.),
        #             op.AND(clElectrons[0].pt > 15., muons[0].pt > 25.))
        #         ))
        # ))

        # lepton channels
        # emuPair = op.combine((clElectrons, muons), N=2,
        #                      pred=lambda el, mu: el.charge != mu.charge)
        # eePair = op.combine(clElectrons, N=2, pred=lambda el1,
        #                     el2: el1.charge != el2.charge)
        # mumuPair = op.combine(muons, N=2, pred=lambda mu1,
        #                       mu2: mu1.charge != mu2.charge)

        # firstEMUpair = emuPair[0]
        # firstEEpair = eePair[0]
        # firstMUMUpair = mumuPair[0]

        # boosted -> and at least one b-tagged ak8 jet
        # DL_boosted = hasTwoL.refine(
        #     'DL_boosted', cut=(op.rng_len(ak8bJets) >= 1))

        # resolved -> and at least two ak4 jets with at least one b-tagged and no ak8 jets
        # DL_resolved = hasTwoL.refine('DL_resolved', cut=(op.AND(op.rng_len(
        #     ak4Jets) >= 2, op.rng_len(ak4bJets) >= 1, op.rng_len(ak8Jets) == 0)))

        ### Semi-leptonic channel ###

        # has exactly one lepton
        # hasOneL = noSel.refine('hasOneL', cut=(op.OR(
        #     op.AND(
        #         op.rng_len(clElectrons) == 1,
        #         op.rng_len(muons) == 0,
        #         clElectrons[0].pt > 32.),
        #     op.AND(
        #         op.rng_len(muons) == 1,
        #         op.rng_len(clElectrons) == 0,
        #         muons[0].pt > 25.)
        # )))

        # ak4ak4bJetPair = op.combine((ak4Jets, ak4bJets), N=2, pred=lambda j1, j2:
        #                             op.deltaR(j1.p4, j2.p4) > 0.8)
        # firstJetPair = ak4ak4bJetPair[0]

        # boosted -> and at least one b-tagged ak8 jet and at least one ak4 jet outside the b-tagged ak8 jet
        # SL_boosted = hasOneL.refine('SL_boosted', cut=(op.AND(
        #     op.rng_len(ak8bJets) >= 1,
        #     op.rng_len(ak4Jets) >= 1,
        #     op.deltaR(ak4Jets[0].p4, ak8bJets[0].p4) >= 1.2)
        # ))
        # resolved -> and at least three ak4 jets with at least one b-tagged and no ak8 jets
        # SL_resolved = hasOneL.refine('SL_resolved', cut=(op.AND(op.rng_len(
        #     ak4Jets) >= 3, op.rng_len(ak4bJets) >= 1, op.rng_len(ak8Jets) == 0)
        # ))

        #############################################################################
        #                                 Plots                                     #
        #############################################################################
        plots.extend([
            Plot.make1D("nFakeElectrons", op.rng_len(fakeElectrons), noSel, EqBin(
                15, 0., 15.), xTitle="Number of fake electrons"),
            # Plot.make1D("nFakeMuons", op.rng_len(fakeMuons), noSel, EqBin(
            #     15, 0., 15.), xTitle="Number of fake muons"),
            # Plot.make1D("ncleanedAK8Jets", op.rng_len(cleanedAK8Jets), noSel, EqBin(
            #     15, 0., 15.), xTitle="Number of cleaned AK8 jets"),
            # Plot.make1D("nTaus", op.rng_len(taus), noSel, EqBin(
            #     15, 0., 15.), xTitle="Number of taus"),
            # Plot.make1D("nCleanedTaus", op.rng_len(cleanedTaus), noSel, EqBin(
            #     15, 0., 15.), xTitle="Number of cleaned taus")
        ])

        # Cutflow report
        # yields.add(hasOneL, 'one lepton')
        # yields.add(hasTwoL, 'two leptons')
        # yields.add(DL_boosted, 'DL boosted')
        # # yields.add(DL_resolved, 'DL resolved')
        # yields.add(SL_boosted, 'SL boosted')
        # # yields.add(SL_resolved, 'SL resolved')

        return plots
