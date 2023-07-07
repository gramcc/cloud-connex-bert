from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class CustomField(Base):
    __tablename__ = 'sfdc_customfields'

    id = Column(Integer, primary_key=True)
    CustomObjectId = Column(Integer, ForeignKey('customobjects.CustomHelpId'))
    DeveloperName = Column(String)
    ManageableState = Column(Enum("beta", "deleted", "deprecated", "deprecatedEditable", "installed", "installedEditable", "released", "unmanaged", name="manageablestate_enum"))
    Metadata = Column(String) # This could be a JSON or another table as per your requirement
    NamespacePrefix = Column(String)
    TableEnumOrId = Column(String) # This could be an enum as per your requirement

    custom_object = relationship("CustomObject", back_populates="custom_fields")

class CustomObject(Base):
    __tablename__ = 'sfdc_customobjects'

    id = Column(Integer, primary_key=True)
    CustomHelpId = Column(Integer)
    Description = Column(String)
    DeveloperName = Column(String)
    ExternalName = Column(String)
    ExternalRepository = Column(String)
    Language = Column(String)
    ManageableState = Column(Enum("beta", "deleted", "deprecated", "deprecatedEditable", "installed", "installedEditable", "released", "unmanaged", name="manageablestate_enum"))
    NamespacePrefix = Column(String)
    SharingModel = Column(Enum("Edit", "ControlledByParent", "None", "Read", name="sharingmodel_enum"))

    custom_fields = relationship("CustomField", back_populates="custom_object")