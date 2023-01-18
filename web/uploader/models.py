from django.db import models
from pymatgen.core.structure import IStructure
import pandas as pd
from matminer.featurizers.base import MultipleFeaturizer
from matminer.featurizers.composition import ElementProperty, Stoichiometry, ValenceOrbital, IonProperty
from matminer.featurizers.structure import SiteStatsFingerprint, StructuralHeterogeneity, ChemicalOrdering, StructureComposition, MaximumPackingEfficiency
import pickle

class Upload(models.Model):
    upload_file = models.FileField()    
    upload_date = models.DateTimeField(auto_now_add =True)
    
    featurizer = MultipleFeaturizer([
    SiteStatsFingerprint.from_preset("CoordinationNumber_ward-prb-2017"),
    StructuralHeterogeneity(),
    ChemicalOrdering(),
    MaximumPackingEfficiency(),
    SiteStatsFingerprint.from_preset("LocalPropertyDifference_ward-prb-2017"),
    StructureComposition(Stoichiometry()),
    StructureComposition(ElementProperty.from_preset("magpie")),
    StructureComposition(ValenceOrbital(props=['frac'])),
    StructureComposition(IonProperty(fast=True))
    ])

    model_path = '/path/to/ml/folder'
    classifier = pickle.load(open(model_path + "/ml/rf_classifier_trained.p", "rb"))
    regressor = pickle.load(open(model_path + "/ml/krr_regressor_trained.p", "rb"))
    features_to_keep = pickle.load(open(model_path + "/ml/feature_columns.p", "rb"))
    reg_features_to_keep = pickle.load(open(model_path + "/ml/reg_keep_feat.p", "rb"))
    topology = pickle.load(open(model_path + "/ml/rf_topology_trained.p", "rb"))
    top_features_to_keep = pickle.load(open(model_path + "/ml/top_columns.p", "rb"))

    def get_system_name(self):
        try:
            structure = IStructure.from_file(self.upload_file.path)
            elements = [x['species'][0]['element'] for x in structure.as_dict()['sites']]
            counts = [[element, elements.count(element)] for element in elements]
            name_scheme = []
            for count in counts:
                if count not in name_scheme:
                    name_scheme.append(count)
            for i in range(len(name_scheme)):
                if name_scheme[i][1] == 1:
                    name_scheme[i][1] = ''
            name = [x[0] + str(x[1]) for x in name_scheme]
            return ''.join(name)
        except:
            return 'File could not be read.'
    
    def get_electronic_characterization(self):
        structure = IStructure.from_file(self.upload_file.path)
        pred_df = pd.DataFrame(columns = ['structure'])
        pred_df.loc[0, 'structure'] = structure
        pred_df = self.featurizer.featurize_dataframe(pred_df, 'structure', ignore_errors = True)
        del pred_df['structure']
        to_drop_class = [column for column in pred_df.columns if column not in self.features_to_keep]
        pred_df_class = pred_df.drop(pred_df[to_drop_class], axis = 1)
        classification = self.classifier.predict(pred_df_class)[0]
        if classification == 1:
            to_drop_reg = [column for column in pred_df.columns if column not in self.reg_features_to_keep]
            pred_df_reg = pred_df.drop(pred_df[to_drop_reg], axis = 1)
            gap = self.regressor.predict(pred_df_reg)[0]
            return 'insulator with \u0394 = %0.2f eV' % gap
        return 'metal'

    def get_topological_characterization(self):
        structure = IStructure.from_file(self.upload_file.path)
        electronic = self.get_electronic_characterization()
        if electronic[0] == 'm':
            gap = 0.0
        else:
            gap = float(electronic.split()[-2])
        pred_df = pd.DataFrame(columns = ['structure'])
        pred_df.loc[0, 'structure'] = structure
        pred_df = self.featurizer.featurize_dataframe(pred_df, 'structure', ignore_errors = True)
        del pred_df['structure']
        to_drop_class = [column for column in pred_df.columns if column not in self.top_features_to_keep]
        pred_df_class = pred_df.drop(pred_df[to_drop_class], axis = 1)
        pred_df_class.loc[0, 'gap pbe'] = gap
        classification = self.topology.predict(pred_df_class)[0]
        if classification == 0:
            return 'trivial'
        return 'non-trivial'