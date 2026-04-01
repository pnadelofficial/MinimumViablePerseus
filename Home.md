We're building a _minimal_ replacement for the aging Perseus 4. We are guided by the following principles:

1. The system must be _stable_: it should not rely excessively on external libraries or frameworks.
2. The system must be _sustainable_: it should have a clean architecture based on modern software design principles.
3. The system must be _maintainable_: it should be thoroughly documented so that future developers may support and extend it.

Some consequences of these principles:

1. We will reproduce the features of P4 only; we will not, in the first stage, add any of the features and functionalities Perseus has developed since P4's release.
2. We will develop code using languages familiar to the Perseus community: Python; XSLT; XQuery.
3. We will avoid using JavaScript whenever possible to avoid incurring technical debt from a rapidly changing ecosystem.