package org.gradle.accessors.dm;

import org.gradle.api.NonNullApi;
import org.gradle.api.artifacts.MinimalExternalModuleDependency;
import org.gradle.plugin.use.PluginDependency;
import org.gradle.api.artifacts.ExternalModuleDependencyBundle;
import org.gradle.api.artifacts.MutableVersionConstraint;
import org.gradle.api.provider.Provider;
import org.gradle.api.model.ObjectFactory;
import org.gradle.api.provider.ProviderFactory;
import org.gradle.api.internal.catalog.AbstractExternalDependencyFactory;
import org.gradle.api.internal.catalog.DefaultVersionCatalog;
import java.util.Map;
import org.gradle.api.internal.attributes.AttributesFactory;
import org.gradle.api.internal.artifacts.dsl.CapabilityNotationParser;
import javax.inject.Inject;

/**
 * A catalog of dependencies accessible via the {@code libs} extension.
 */
@NonNullApi
public class LibrariesForLibs extends AbstractExternalDependencyFactory {

    private final AbstractExternalDependencyFactory owner = this;
    private final DockingframesLibraryAccessors laccForDockingframesLibraryAccessors = new DockingframesLibraryAccessors(owner);
    private final GestaltLibraryAccessors laccForGestaltLibraryAccessors = new GestaltLibraryAccessors(owner);
    private final GuiceLibraryAccessors laccForGuiceLibraryAccessors = new GuiceLibraryAccessors(owner);
    private final HuxhornLibraryAccessors laccForHuxhornLibraryAccessors = new HuxhornLibraryAccessors(owner);
    private final JacksonLibraryAccessors laccForJacksonLibraryAccessors = new JacksonLibraryAccessors(owner);
    private final JakartaLibraryAccessors laccForJakartaLibraryAccessors = new JakartaLibraryAccessors(owner);
    private final JavalinLibraryAccessors laccForJavalinLibraryAccessors = new JavalinLibraryAccessors(owner);
    private final JaxbLibraryAccessors laccForJaxbLibraryAccessors = new JaxbLibraryAccessors(owner);
    private final JgraphtLibraryAccessors laccForJgraphtLibraryAccessors = new JgraphtLibraryAccessors(owner);
    private final JtsLibraryAccessors laccForJtsLibraryAccessors = new JtsLibraryAccessors(owner);
    private final JunitLibraryAccessors laccForJunitLibraryAccessors = new JunitLibraryAccessors(owner);
    private final OpenapiLibraryAccessors laccForOpenapiLibraryAccessors = new OpenapiLibraryAccessors(owner);
    private final Slf4jLibraryAccessors laccForSlf4jLibraryAccessors = new Slf4jLibraryAccessors(owner);
    private final SwaggerLibraryAccessors laccForSwaggerLibraryAccessors = new SwaggerLibraryAccessors(owner);
    private final VersionAccessors vaccForVersionAccessors = new VersionAccessors(providers, config);
    private final BundleAccessors baccForBundleAccessors = new BundleAccessors(objects, providers, config, attributesFactory, capabilityNotationParser);
    private final PluginAccessors paccForPluginAccessors = new PluginAccessors(providers, config);

    @Inject
    public LibrariesForLibs(DefaultVersionCatalog config, ProviderFactory providers, ObjectFactory objects, AttributesFactory attributesFactory, CapabilityNotationParser capabilityNotationParser) {
        super(config, providers, objects, attributesFactory, capabilityNotationParser);
    }

    /**
     * Dependency provider for <b>approvaltests</b> with <b>com.approvaltests:approvaltests</b> coordinates and
     * with version reference <b>approvaltests</b>
     * <p>
     * This dependency was declared in catalog libs.versions.toml
     */
    public Provider<MinimalExternalModuleDependency> getApprovaltests() {
        return create("approvaltests");
    }

    /**
     * Dependency provider for <b>assertj</b> with <b>org.assertj:assertj-core</b> coordinates and
     * with version reference <b>assertj</b>
     * <p>
     * This dependency was declared in catalog libs.versions.toml
     */
    public Provider<MinimalExternalModuleDependency> getAssertj() {
        return create("assertj");
    }

    /**
     * Dependency provider for <b>hamcrest</b> with <b>org.hamcrest:hamcrest</b> coordinates and
     * with version reference <b>hamcrest</b>
     * <p>
     * This dependency was declared in catalog libs.versions.toml
     */
    public Provider<MinimalExternalModuleDependency> getHamcrest() {
        return create("hamcrest");
    }

    /**
     * Dependency provider for <b>jhotdraw</b> with <b>org.opentcs.thirdparty.jhotdraw:jhotdraw</b> coordinates and
     * with version reference <b>jhotdraw</b>
     * <p>
     * This dependency was declared in catalog libs.versions.toml
     */
    public Provider<MinimalExternalModuleDependency> getJhotdraw() {
        return create("jhotdraw");
    }

    /**
     * Dependency provider for <b>mockito</b> with <b>org.mockito:mockito-core</b> coordinates and
     * with version reference <b>mockito</b>
     * <p>
     * This dependency was declared in catalog libs.versions.toml
     */
    public Provider<MinimalExternalModuleDependency> getMockito() {
        return create("mockito");
    }

    /**
     * Dependency provider for <b>modelmapper</b> with <b>org.modelmapper:modelmapper</b> coordinates and
     * with version reference <b>modelmapper</b>
     * <p>
     * This dependency was declared in catalog libs.versions.toml
     */
    public Provider<MinimalExternalModuleDependency> getModelmapper() {
        return create("modelmapper");
    }

    /**
     * Dependency provider for <b>semver4j</b> with <b>org.semver4j:semver4j</b> coordinates and
     * with version reference <b>semver4j</b>
     * <p>
     * This dependency was declared in catalog libs.versions.toml
     */
    public Provider<MinimalExternalModuleDependency> getSemver4j() {
        return create("semver4j");
    }

    /**
     * Group of libraries at <b>dockingframes</b>
     */
    public DockingframesLibraryAccessors getDockingframes() {
        return laccForDockingframesLibraryAccessors;
    }

    /**
     * Group of libraries at <b>gestalt</b>
     */
    public GestaltLibraryAccessors getGestalt() {
        return laccForGestaltLibraryAccessors;
    }

    /**
     * Group of libraries at <b>guice</b>
     */
    public GuiceLibraryAccessors getGuice() {
        return laccForGuiceLibraryAccessors;
    }

    /**
     * Group of libraries at <b>huxhorn</b>
     */
    public HuxhornLibraryAccessors getHuxhorn() {
        return laccForHuxhornLibraryAccessors;
    }

    /**
     * Group of libraries at <b>jackson</b>
     */
    public JacksonLibraryAccessors getJackson() {
        return laccForJacksonLibraryAccessors;
    }

    /**
     * Group of libraries at <b>jakarta</b>
     */
    public JakartaLibraryAccessors getJakarta() {
        return laccForJakartaLibraryAccessors;
    }

    /**
     * Group of libraries at <b>javalin</b>
     */
    public JavalinLibraryAccessors getJavalin() {
        return laccForJavalinLibraryAccessors;
    }

    /**
     * Group of libraries at <b>jaxb</b>
     */
    public JaxbLibraryAccessors getJaxb() {
        return laccForJaxbLibraryAccessors;
    }

    /**
     * Group of libraries at <b>jgrapht</b>
     */
    public JgraphtLibraryAccessors getJgrapht() {
        return laccForJgraphtLibraryAccessors;
    }

    /**
     * Group of libraries at <b>jts</b>
     */
    public JtsLibraryAccessors getJts() {
        return laccForJtsLibraryAccessors;
    }

    /**
     * Group of libraries at <b>junit</b>
     */
    public JunitLibraryAccessors getJunit() {
        return laccForJunitLibraryAccessors;
    }

    /**
     * Group of libraries at <b>openapi</b>
     */
    public OpenapiLibraryAccessors getOpenapi() {
        return laccForOpenapiLibraryAccessors;
    }

    /**
     * Group of libraries at <b>slf4j</b>
     */
    public Slf4jLibraryAccessors getSlf4j() {
        return laccForSlf4jLibraryAccessors;
    }

    /**
     * Group of libraries at <b>swagger</b>
     */
    public SwaggerLibraryAccessors getSwagger() {
        return laccForSwaggerLibraryAccessors;
    }

    /**
     * Group of versions at <b>versions</b>
     */
    public VersionAccessors getVersions() {
        return vaccForVersionAccessors;
    }

    /**
     * Group of bundles at <b>bundles</b>
     */
    public BundleAccessors getBundles() {
        return baccForBundleAccessors;
    }

    /**
     * Group of plugins at <b>plugins</b>
     */
    public PluginAccessors getPlugins() {
        return paccForPluginAccessors;
    }

    public static class DockingframesLibraryAccessors extends SubDependencyFactory {

        public DockingframesLibraryAccessors(AbstractExternalDependencyFactory owner) { super(owner); }

        /**
         * Dependency provider for <b>common</b> with <b>org.opentcs.thirdparty.dockingframes:docking-frames-common</b> coordinates and
         * with version reference <b>dockingframes</b>
         * <p>
         * This dependency was declared in catalog libs.versions.toml
         */
        public Provider<MinimalExternalModuleDependency> getCommon() {
            return create("dockingframes.common");
        }

        /**
         * Dependency provider for <b>core</b> with <b>org.opentcs.thirdparty.dockingframes:docking-frames-core</b> coordinates and
         * with version reference <b>dockingframes</b>
         * <p>
         * This dependency was declared in catalog libs.versions.toml
         */
        public Provider<MinimalExternalModuleDependency> getCore() {
            return create("dockingframes.core");
        }

    }

    public static class GestaltLibraryAccessors extends SubDependencyFactory {

        public GestaltLibraryAccessors(AbstractExternalDependencyFactory owner) { super(owner); }

        /**
         * Dependency provider for <b>core</b> with <b>com.github.gestalt-config:gestalt-core</b> coordinates and
         * with version reference <b>gestalt</b>
         * <p>
         * This dependency was declared in catalog libs.versions.toml
         */
        public Provider<MinimalExternalModuleDependency> getCore() {
            return create("gestalt.core");
        }

    }

    public static class GuiceLibraryAccessors extends SubDependencyFactory implements DependencyNotationSupplier {

        public GuiceLibraryAccessors(AbstractExternalDependencyFactory owner) { super(owner); }

        /**
         * Dependency provider for <b>guice</b> with <b>com.google.inject:guice</b> coordinates and
         * with version reference <b>guice</b>
         * <p>
         * This dependency was declared in catalog libs.versions.toml
         */
        public Provider<MinimalExternalModuleDependency> asProvider() {
            return create("guice");
        }

        /**
         * Dependency provider for <b>assistedinject</b> with <b>com.google.inject.extensions:guice-assistedinject</b> coordinates and
         * with version reference <b>guice</b>
         * <p>
         * This dependency was declared in catalog libs.versions.toml
         */
        public Provider<MinimalExternalModuleDependency> getAssistedinject() {
            return create("guice.assistedinject");
        }

    }

    public static class HuxhornLibraryAccessors extends SubDependencyFactory {
        private final HuxhornSulkyLibraryAccessors laccForHuxhornSulkyLibraryAccessors = new HuxhornSulkyLibraryAccessors(owner);

        public HuxhornLibraryAccessors(AbstractExternalDependencyFactory owner) { super(owner); }

        /**
         * Group of libraries at <b>huxhorn.sulky</b>
         */
        public HuxhornSulkyLibraryAccessors getSulky() {
            return laccForHuxhornSulkyLibraryAccessors;
        }

    }

    public static class HuxhornSulkyLibraryAccessors extends SubDependencyFactory {

        public HuxhornSulkyLibraryAccessors(AbstractExternalDependencyFactory owner) { super(owner); }

        /**
         * Dependency provider for <b>ulid</b> with <b>de.huxhorn.sulky:de.huxhorn.sulky.ulid</b> coordinates and
         * with version reference <b>huxhorn.sulky.ulid</b>
         * <p>
         * This dependency was declared in catalog libs.versions.toml
         */
        public Provider<MinimalExternalModuleDependency> getUlid() {
            return create("huxhorn.sulky.ulid");
        }

    }

    public static class JacksonLibraryAccessors extends SubDependencyFactory {
        private final JacksonDatatypeLibraryAccessors laccForJacksonDatatypeLibraryAccessors = new JacksonDatatypeLibraryAccessors(owner);
        private final JacksonModuleLibraryAccessors laccForJacksonModuleLibraryAccessors = new JacksonModuleLibraryAccessors(owner);

        public JacksonLibraryAccessors(AbstractExternalDependencyFactory owner) { super(owner); }

        /**
         * Dependency provider for <b>databind</b> with <b>com.fasterxml.jackson.core:jackson-databind</b> coordinates and
         * with version reference <b>jackson</b>
         * <p>
         * This dependency was declared in catalog libs.versions.toml
         */
        public Provider<MinimalExternalModuleDependency> getDatabind() {
            return create("jackson.databind");
        }

        /**
         * Group of libraries at <b>jackson.datatype</b>
         */
        public JacksonDatatypeLibraryAccessors getDatatype() {
            return laccForJacksonDatatypeLibraryAccessors;
        }

        /**
         * Group of libraries at <b>jackson.module</b>
         */
        public JacksonModuleLibraryAccessors getModule() {
            return laccForJacksonModuleLibraryAccessors;
        }

    }

    public static class JacksonDatatypeLibraryAccessors extends SubDependencyFactory {

        public JacksonDatatypeLibraryAccessors(AbstractExternalDependencyFactory owner) { super(owner); }

        /**
         * Dependency provider for <b>jsr310</b> with <b>com.fasterxml.jackson.datatype:jackson-datatype-jsr310</b> coordinates and
         * with version reference <b>jackson</b>
         * <p>
         * This dependency was declared in catalog libs.versions.toml
         */
        public Provider<MinimalExternalModuleDependency> getJsr310() {
            return create("jackson.datatype.jsr310");
        }

    }

    public static class JacksonModuleLibraryAccessors extends SubDependencyFactory {

        public JacksonModuleLibraryAccessors(AbstractExternalDependencyFactory owner) { super(owner); }

        /**
         * Dependency provider for <b>jsonSchema</b> with <b>com.fasterxml.jackson.module:jackson-module-jsonSchema</b> coordinates and
         * with version reference <b>jackson</b>
         * <p>
         * This dependency was declared in catalog libs.versions.toml
         */
        public Provider<MinimalExternalModuleDependency> getJsonSchema() {
            return create("jackson.module.jsonSchema");
        }

    }

    public static class JakartaLibraryAccessors extends SubDependencyFactory {

        public JakartaLibraryAccessors(AbstractExternalDependencyFactory owner) { super(owner); }

        /**
         * Dependency provider for <b>annotation</b> with <b>jakarta.annotation:jakarta.annotation-api</b> coordinates and
         * with version reference <b>jakarta.annotation</b>
         * <p>
         * This dependency was declared in catalog libs.versions.toml
         */
        public Provider<MinimalExternalModuleDependency> getAnnotation() {
            return create("jakarta.annotation");
        }

        /**
         * Dependency provider for <b>inject</b> with <b>jakarta.inject:jakarta.inject-api</b> coordinates and
         * with version reference <b>jakarta.inject</b>
         * <p>
         * This dependency was declared in catalog libs.versions.toml
         */
        public Provider<MinimalExternalModuleDependency> getInject() {
            return create("jakarta.inject");
        }

    }

    public static class JavalinLibraryAccessors extends SubDependencyFactory implements DependencyNotationSupplier {
        private final JavalinSslLibraryAccessors laccForJavalinSslLibraryAccessors = new JavalinSslLibraryAccessors(owner);

        public JavalinLibraryAccessors(AbstractExternalDependencyFactory owner) { super(owner); }

        /**
         * Dependency provider for <b>javalin</b> with <b>io.javalin:javalin</b> coordinates and
         * with version reference <b>javalin</b>
         * <p>
         * This dependency was declared in catalog libs.versions.toml
         */
        public Provider<MinimalExternalModuleDependency> asProvider() {
            return create("javalin");
        }

        /**
         * Group of libraries at <b>javalin.ssl</b>
         */
        public JavalinSslLibraryAccessors getSsl() {
            return laccForJavalinSslLibraryAccessors;
        }

    }

    public static class JavalinSslLibraryAccessors extends SubDependencyFactory {

        public JavalinSslLibraryAccessors(AbstractExternalDependencyFactory owner) { super(owner); }

        /**
         * Dependency provider for <b>plugin</b> with <b>io.javalin.community.ssl:ssl-plugin</b> coordinates and
         * with version reference <b>javalin.ssl.plugin</b>
         * <p>
         * This dependency was declared in catalog libs.versions.toml
         */
        public Provider<MinimalExternalModuleDependency> getPlugin() {
            return create("javalin.ssl.plugin");
        }

    }

    public static class JaxbLibraryAccessors extends SubDependencyFactory {

        public JaxbLibraryAccessors(AbstractExternalDependencyFactory owner) { super(owner); }

        /**
         * Dependency provider for <b>runtime</b> with <b>org.glassfish.jaxb:jaxb-runtime</b> coordinates and
         * with version reference <b>jaxb</b>
         * <p>
         * This dependency was declared in catalog libs.versions.toml
         */
        public Provider<MinimalExternalModuleDependency> getRuntime() {
            return create("jaxb.runtime");
        }

    }

    public static class JgraphtLibraryAccessors extends SubDependencyFactory {

        public JgraphtLibraryAccessors(AbstractExternalDependencyFactory owner) { super(owner); }

        /**
         * Dependency provider for <b>core</b> with <b>org.jgrapht:jgrapht-core</b> coordinates and
         * with version reference <b>jgrapht.core</b>
         * <p>
         * This dependency was declared in catalog libs.versions.toml
         */
        public Provider<MinimalExternalModuleDependency> getCore() {
            return create("jgrapht.core");
        }

    }

    public static class JtsLibraryAccessors extends SubDependencyFactory {

        public JtsLibraryAccessors(AbstractExternalDependencyFactory owner) { super(owner); }

        /**
         * Dependency provider for <b>core</b> with <b>org.locationtech.jts:jts-core</b> coordinates and
         * with version reference <b>jts.core</b>
         * <p>
         * This dependency was declared in catalog libs.versions.toml
         */
        public Provider<MinimalExternalModuleDependency> getCore() {
            return create("jts.core");
        }

    }

    public static class JunitLibraryAccessors extends SubDependencyFactory {
        private final JunitJupiterLibraryAccessors laccForJunitJupiterLibraryAccessors = new JunitJupiterLibraryAccessors(owner);
        private final JunitPlatformLibraryAccessors laccForJunitPlatformLibraryAccessors = new JunitPlatformLibraryAccessors(owner);

        public JunitLibraryAccessors(AbstractExternalDependencyFactory owner) { super(owner); }

        /**
         * Group of libraries at <b>junit.jupiter</b>
         */
        public JunitJupiterLibraryAccessors getJupiter() {
            return laccForJunitJupiterLibraryAccessors;
        }

        /**
         * Group of libraries at <b>junit.platform</b>
         */
        public JunitPlatformLibraryAccessors getPlatform() {
            return laccForJunitPlatformLibraryAccessors;
        }

    }

    public static class JunitJupiterLibraryAccessors extends SubDependencyFactory {

        public JunitJupiterLibraryAccessors(AbstractExternalDependencyFactory owner) { super(owner); }

        /**
         * Dependency provider for <b>api</b> with <b>org.junit.jupiter:junit-jupiter-api</b> coordinates and
         * with version reference <b>junit</b>
         * <p>
         * This dependency was declared in catalog libs.versions.toml
         */
        public Provider<MinimalExternalModuleDependency> getApi() {
            return create("junit.jupiter.api");
        }

        /**
         * Dependency provider for <b>engine</b> with <b>org.junit.jupiter:junit-jupiter-engine</b> coordinates and
         * with version reference <b>junit</b>
         * <p>
         * This dependency was declared in catalog libs.versions.toml
         */
        public Provider<MinimalExternalModuleDependency> getEngine() {
            return create("junit.jupiter.engine");
        }

        /**
         * Dependency provider for <b>params</b> with <b>org.junit.jupiter:junit-jupiter-params</b> coordinates and
         * with version reference <b>junit</b>
         * <p>
         * This dependency was declared in catalog libs.versions.toml
         */
        public Provider<MinimalExternalModuleDependency> getParams() {
            return create("junit.jupiter.params");
        }

    }

    public static class JunitPlatformLibraryAccessors extends SubDependencyFactory {

        public JunitPlatformLibraryAccessors(AbstractExternalDependencyFactory owner) { super(owner); }

        /**
         * Dependency provider for <b>launcher</b> with <b>org.junit.platform:junit-platform-launcher</b> coordinates and
         * with version reference <b>junit.platform.launcher</b>
         * <p>
         * This dependency was declared in catalog libs.versions.toml
         */
        public Provider<MinimalExternalModuleDependency> getLauncher() {
            return create("junit.platform.launcher");
        }

    }

    public static class OpenapiLibraryAccessors extends SubDependencyFactory {
        private final OpenapiGeneratorLibraryAccessors laccForOpenapiGeneratorLibraryAccessors = new OpenapiGeneratorLibraryAccessors(owner);

        public OpenapiLibraryAccessors(AbstractExternalDependencyFactory owner) { super(owner); }

        /**
         * Group of libraries at <b>openapi.generator</b>
         */
        public OpenapiGeneratorLibraryAccessors getGenerator() {
            return laccForOpenapiGeneratorLibraryAccessors;
        }

    }

    public static class OpenapiGeneratorLibraryAccessors extends SubDependencyFactory {

        public OpenapiGeneratorLibraryAccessors(AbstractExternalDependencyFactory owner) { super(owner); }

        /**
         * Dependency provider for <b>cli</b> with <b>org.openapitools:openapi-generator-cli</b> coordinates and
         * with version reference <b>openapi.generator.cli</b>
         * <p>
         * This dependency was declared in catalog libs.versions.toml
         */
        public Provider<MinimalExternalModuleDependency> getCli() {
            return create("openapi.generator.cli");
        }

    }

    public static class Slf4jLibraryAccessors extends SubDependencyFactory {

        public Slf4jLibraryAccessors(AbstractExternalDependencyFactory owner) { super(owner); }

        /**
         * Dependency provider for <b>api</b> with <b>org.slf4j:slf4j-api</b> coordinates and
         * with version reference <b>slf4j</b>
         * <p>
         * This dependency was declared in catalog libs.versions.toml
         */
        public Provider<MinimalExternalModuleDependency> getApi() {
            return create("slf4j.api");
        }

        /**
         * Dependency provider for <b>jdk14</b> with <b>org.slf4j:slf4j-jdk14</b> coordinates and
         * with version reference <b>slf4j</b>
         * <p>
         * This dependency was declared in catalog libs.versions.toml
         */
        public Provider<MinimalExternalModuleDependency> getJdk14() {
            return create("slf4j.jdk14");
        }

    }

    public static class SwaggerLibraryAccessors extends SubDependencyFactory {

        public SwaggerLibraryAccessors(AbstractExternalDependencyFactory owner) { super(owner); }

        /**
         * Dependency provider for <b>ui</b> with <b>org.webjars:swagger-ui</b> coordinates and
         * with version reference <b>swagger.ui</b>
         * <p>
         * This dependency was declared in catalog libs.versions.toml
         */
        public Provider<MinimalExternalModuleDependency> getUi() {
            return create("swagger.ui");
        }

    }

    public static class VersionAccessors extends VersionFactory  {

        private final DependencyVersionAccessors vaccForDependencyVersionAccessors = new DependencyVersionAccessors(providers, config);
        private final FreefairVersionAccessors vaccForFreefairVersionAccessors = new FreefairVersionAccessors(providers, config);
        private final GradleVersionAccessors vaccForGradleVersionAccessors = new GradleVersionAccessors(providers, config);
        private final HuxhornVersionAccessors vaccForHuxhornVersionAccessors = new HuxhornVersionAccessors(providers, config);
        private final JakartaVersionAccessors vaccForJakartaVersionAccessors = new JakartaVersionAccessors(providers, config);
        private final JavalinVersionAccessors vaccForJavalinVersionAccessors = new JavalinVersionAccessors(providers, config);
        private final JgraphtVersionAccessors vaccForJgraphtVersionAccessors = new JgraphtVersionAccessors(providers, config);
        private final JtsVersionAccessors vaccForJtsVersionAccessors = new JtsVersionAccessors(providers, config);
        private final JunitVersionAccessors vaccForJunitVersionAccessors = new JunitVersionAccessors(providers, config);
        private final OpenapiVersionAccessors vaccForOpenapiVersionAccessors = new OpenapiVersionAccessors(providers, config);
        private final SwaggerVersionAccessors vaccForSwaggerVersionAccessors = new SwaggerVersionAccessors(providers, config);
        public VersionAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Version alias <b>approvaltests</b> with value <b>26.4.0</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> getApprovaltests() { return getVersion("approvaltests"); }

        /**
         * Version alias <b>asciidoctor</b> with value <b>4.0.5</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> getAsciidoctor() { return getVersion("asciidoctor"); }

        /**
         * Version alias <b>assertj</b> with value <b>3.27.6</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> getAssertj() { return getVersion("assertj"); }

        /**
         * Version alias <b>dockingframes</b> with value <b>1.1.2p11</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> getDockingframes() { return getVersion("dockingframes"); }

        /**
         * Version alias <b>gestalt</b> with value <b>0.37.0</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> getGestalt() { return getVersion("gestalt"); }

        /**
         * Version alias <b>guice</b> with value <b>7.0.0</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> getGuice() { return getVersion("guice"); }

        /**
         * Version alias <b>hamcrest</b> with value <b>3.0</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> getHamcrest() { return getVersion("hamcrest"); }

        /**
         * Version alias <b>jackson</b> with value <b>2.20.0</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> getJackson() { return getVersion("jackson"); }

        /**
         * Version alias <b>jacocolog</b> with value <b>3.1.0</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> getJacocolog() { return getVersion("jacocolog"); }

        /**
         * Version alias <b>jaxb</b> with value <b>4.0.6</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> getJaxb() { return getVersion("jaxb"); }

        /**
         * Version alias <b>jhotdraw</b> with value <b>7.6.20190506</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> getJhotdraw() { return getVersion("jhotdraw"); }

        /**
         * Version alias <b>mockito</b> with value <b>5.21.0</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> getMockito() { return getVersion("mockito"); }

        /**
         * Version alias <b>modelmapper</b> with value <b>3.2.5</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> getModelmapper() { return getVersion("modelmapper"); }

        /**
         * Version alias <b>semver4j</b> with value <b>6.0.0</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> getSemver4j() { return getVersion("semver4j"); }

        /**
         * Version alias <b>slf4j</b> with value <b>2.0.17</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> getSlf4j() { return getVersion("slf4j"); }

        /**
         * Version alias <b>spotless</b> with value <b>8.1.0</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> getSpotless() { return getVersion("spotless"); }

        /**
         * Group of versions at <b>versions.dependency</b>
         */
        public DependencyVersionAccessors getDependency() {
            return vaccForDependencyVersionAccessors;
        }

        /**
         * Group of versions at <b>versions.freefair</b>
         */
        public FreefairVersionAccessors getFreefair() {
            return vaccForFreefairVersionAccessors;
        }

        /**
         * Group of versions at <b>versions.gradle</b>
         */
        public GradleVersionAccessors getGradle() {
            return vaccForGradleVersionAccessors;
        }

        /**
         * Group of versions at <b>versions.huxhorn</b>
         */
        public HuxhornVersionAccessors getHuxhorn() {
            return vaccForHuxhornVersionAccessors;
        }

        /**
         * Group of versions at <b>versions.jakarta</b>
         */
        public JakartaVersionAccessors getJakarta() {
            return vaccForJakartaVersionAccessors;
        }

        /**
         * Group of versions at <b>versions.javalin</b>
         */
        public JavalinVersionAccessors getJavalin() {
            return vaccForJavalinVersionAccessors;
        }

        /**
         * Group of versions at <b>versions.jgrapht</b>
         */
        public JgraphtVersionAccessors getJgrapht() {
            return vaccForJgraphtVersionAccessors;
        }

        /**
         * Group of versions at <b>versions.jts</b>
         */
        public JtsVersionAccessors getJts() {
            return vaccForJtsVersionAccessors;
        }

        /**
         * Group of versions at <b>versions.junit</b>
         */
        public JunitVersionAccessors getJunit() {
            return vaccForJunitVersionAccessors;
        }

        /**
         * Group of versions at <b>versions.openapi</b>
         */
        public OpenapiVersionAccessors getOpenapi() {
            return vaccForOpenapiVersionAccessors;
        }

        /**
         * Group of versions at <b>versions.swagger</b>
         */
        public SwaggerVersionAccessors getSwagger() {
            return vaccForSwaggerVersionAccessors;
        }

    }

    public static class DependencyVersionAccessors extends VersionFactory  {

        private final DependencyLicenseVersionAccessors vaccForDependencyLicenseVersionAccessors = new DependencyLicenseVersionAccessors(providers, config);
        public DependencyVersionAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Group of versions at <b>versions.dependency.license</b>
         */
        public DependencyLicenseVersionAccessors getLicense() {
            return vaccForDependencyLicenseVersionAccessors;
        }

    }

    public static class DependencyLicenseVersionAccessors extends VersionFactory  {

        public DependencyLicenseVersionAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Version alias <b>dependency.license.report</b> with value <b>3.0.1</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> getReport() { return getVersion("dependency.license.report"); }

    }

    public static class FreefairVersionAccessors extends VersionFactory  {

        public FreefairVersionAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Version alias <b>freefair.lombok</b> with value <b>9.1.0</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> getLombok() { return getVersion("freefair.lombok"); }

    }

    public static class GradleVersionAccessors extends VersionFactory  {

        private final GradleNexusVersionAccessors vaccForGradleNexusVersionAccessors = new GradleNexusVersionAccessors(providers, config);
        public GradleVersionAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Group of versions at <b>versions.gradle.nexus</b>
         */
        public GradleNexusVersionAccessors getNexus() {
            return vaccForGradleNexusVersionAccessors;
        }

    }

    public static class GradleNexusVersionAccessors extends VersionFactory  {

        private final GradleNexusPublishVersionAccessors vaccForGradleNexusPublishVersionAccessors = new GradleNexusPublishVersionAccessors(providers, config);
        public GradleNexusVersionAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Group of versions at <b>versions.gradle.nexus.publish</b>
         */
        public GradleNexusPublishVersionAccessors getPublish() {
            return vaccForGradleNexusPublishVersionAccessors;
        }

    }

    public static class GradleNexusPublishVersionAccessors extends VersionFactory  {

        public GradleNexusPublishVersionAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Version alias <b>gradle.nexus.publish.plugin</b> with value <b>2.0.0</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> getPlugin() { return getVersion("gradle.nexus.publish.plugin"); }

    }

    public static class HuxhornVersionAccessors extends VersionFactory  {

        private final HuxhornSulkyVersionAccessors vaccForHuxhornSulkyVersionAccessors = new HuxhornSulkyVersionAccessors(providers, config);
        public HuxhornVersionAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Group of versions at <b>versions.huxhorn.sulky</b>
         */
        public HuxhornSulkyVersionAccessors getSulky() {
            return vaccForHuxhornSulkyVersionAccessors;
        }

    }

    public static class HuxhornSulkyVersionAccessors extends VersionFactory  {

        public HuxhornSulkyVersionAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Version alias <b>huxhorn.sulky.ulid</b> with value <b>8.3.0</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> getUlid() { return getVersion("huxhorn.sulky.ulid"); }

    }

    public static class JakartaVersionAccessors extends VersionFactory  {

        public JakartaVersionAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Version alias <b>jakarta.annotation</b> with value <b>3.0.0</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> getAnnotation() { return getVersion("jakarta.annotation"); }

        /**
         * Version alias <b>jakarta.inject</b> with value <b>2.0.1</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> getInject() { return getVersion("jakarta.inject"); }

    }

    public static class JavalinVersionAccessors extends VersionFactory  implements VersionNotationSupplier {

        private final JavalinSslVersionAccessors vaccForJavalinSslVersionAccessors = new JavalinSslVersionAccessors(providers, config);
        public JavalinVersionAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Version alias <b>javalin</b> with value <b>6.7.0</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> asProvider() { return getVersion("javalin"); }

        /**
         * Group of versions at <b>versions.javalin.ssl</b>
         */
        public JavalinSslVersionAccessors getSsl() {
            return vaccForJavalinSslVersionAccessors;
        }

    }

    public static class JavalinSslVersionAccessors extends VersionFactory  {

        public JavalinSslVersionAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Version alias <b>javalin.ssl.plugin</b> with value <b>6.7.0</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> getPlugin() { return getVersion("javalin.ssl.plugin"); }

    }

    public static class JgraphtVersionAccessors extends VersionFactory  {

        public JgraphtVersionAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Version alias <b>jgrapht.core</b> with value <b>1.5.2</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> getCore() { return getVersion("jgrapht.core"); }

    }

    public static class JtsVersionAccessors extends VersionFactory  {

        public JtsVersionAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Version alias <b>jts.core</b> with value <b>1.20.0</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> getCore() { return getVersion("jts.core"); }

    }

    public static class JunitVersionAccessors extends VersionFactory  implements VersionNotationSupplier {

        private final JunitPlatformVersionAccessors vaccForJunitPlatformVersionAccessors = new JunitPlatformVersionAccessors(providers, config);
        public JunitVersionAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Version alias <b>junit</b> with value <b>6.0.2</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> asProvider() { return getVersion("junit"); }

        /**
         * Group of versions at <b>versions.junit.platform</b>
         */
        public JunitPlatformVersionAccessors getPlatform() {
            return vaccForJunitPlatformVersionAccessors;
        }

    }

    public static class JunitPlatformVersionAccessors extends VersionFactory  {

        public JunitPlatformVersionAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Version alias <b>junit.platform.launcher</b> with value <b>6.0.2</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> getLauncher() { return getVersion("junit.platform.launcher"); }

    }

    public static class OpenapiVersionAccessors extends VersionFactory  {

        private final OpenapiGeneratorVersionAccessors vaccForOpenapiGeneratorVersionAccessors = new OpenapiGeneratorVersionAccessors(providers, config);
        public OpenapiVersionAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Group of versions at <b>versions.openapi.generator</b>
         */
        public OpenapiGeneratorVersionAccessors getGenerator() {
            return vaccForOpenapiGeneratorVersionAccessors;
        }

    }

    public static class OpenapiGeneratorVersionAccessors extends VersionFactory  implements VersionNotationSupplier {

        public OpenapiGeneratorVersionAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Version alias <b>openapi.generator</b> with value <b>7.17.0</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> asProvider() { return getVersion("openapi.generator"); }

        /**
         * Version alias <b>openapi.generator.cli</b> with value <b>7.17.0</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> getCli() { return getVersion("openapi.generator.cli"); }

    }

    public static class SwaggerVersionAccessors extends VersionFactory  {

        public SwaggerVersionAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Version alias <b>swagger.generator</b> with value <b>2.19.2</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> getGenerator() { return getVersion("swagger.generator"); }

        /**
         * Version alias <b>swagger.ui</b> with value <b>5.30.3</b>
         * <p>
         * If the version is a rich version and cannot be represented as a
         * single version string, an empty string is returned.
         * <p>
         * This version was declared in catalog libs.versions.toml
         */
        public Provider<String> getUi() { return getVersion("swagger.ui"); }

    }

    public static class BundleAccessors extends BundleFactory {

        public BundleAccessors(ObjectFactory objects, ProviderFactory providers, DefaultVersionCatalog config, AttributesFactory attributesFactory, CapabilityNotationParser capabilityNotationParser) { super(objects, providers, config, attributesFactory, capabilityNotationParser); }

    }

    public static class PluginAccessors extends PluginFactory {
        private final AsciidocorPluginAccessors paccForAsciidocorPluginAccessors = new AsciidocorPluginAccessors(providers, config);
        private final DependencyPluginAccessors paccForDependencyPluginAccessors = new DependencyPluginAccessors(providers, config);
        private final FreefairPluginAccessors paccForFreefairPluginAccessors = new FreefairPluginAccessors(providers, config);
        private final GradlePluginAccessors paccForGradlePluginAccessors = new GradlePluginAccessors(providers, config);
        private final HidetakePluginAccessors paccForHidetakePluginAccessors = new HidetakePluginAccessors(providers, config);
        private final OpenapiPluginAccessors paccForOpenapiPluginAccessors = new OpenapiPluginAccessors(providers, config);

        public PluginAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Plugin provider for <b>jacocolog</b> with plugin id <b>org.barfuin.gradle.jacocolog</b> and
         * with version reference <b>jacocolog</b>
         * <p>
         * This plugin was declared in catalog libs.versions.toml
         */
        public Provider<PluginDependency> getJacocolog() { return createPlugin("jacocolog"); }

        /**
         * Plugin provider for <b>spotless</b> with plugin id <b>com.diffplug.spotless</b> and
         * with version reference <b>spotless</b>
         * <p>
         * This plugin was declared in catalog libs.versions.toml
         */
        public Provider<PluginDependency> getSpotless() { return createPlugin("spotless"); }

        /**
         * Group of plugins at <b>plugins.asciidocor</b>
         */
        public AsciidocorPluginAccessors getAsciidocor() {
            return paccForAsciidocorPluginAccessors;
        }

        /**
         * Group of plugins at <b>plugins.dependency</b>
         */
        public DependencyPluginAccessors getDependency() {
            return paccForDependencyPluginAccessors;
        }

        /**
         * Group of plugins at <b>plugins.freefair</b>
         */
        public FreefairPluginAccessors getFreefair() {
            return paccForFreefairPluginAccessors;
        }

        /**
         * Group of plugins at <b>plugins.gradle</b>
         */
        public GradlePluginAccessors getGradle() {
            return paccForGradlePluginAccessors;
        }

        /**
         * Group of plugins at <b>plugins.hidetake</b>
         */
        public HidetakePluginAccessors getHidetake() {
            return paccForHidetakePluginAccessors;
        }

        /**
         * Group of plugins at <b>plugins.openapi</b>
         */
        public OpenapiPluginAccessors getOpenapi() {
            return paccForOpenapiPluginAccessors;
        }

    }

    public static class AsciidocorPluginAccessors extends PluginFactory {
        private final AsciidocorJvmPluginAccessors paccForAsciidocorJvmPluginAccessors = new AsciidocorJvmPluginAccessors(providers, config);

        public AsciidocorPluginAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Group of plugins at <b>plugins.asciidocor.jvm</b>
         */
        public AsciidocorJvmPluginAccessors getJvm() {
            return paccForAsciidocorJvmPluginAccessors;
        }

    }

    public static class AsciidocorJvmPluginAccessors extends PluginFactory {

        public AsciidocorJvmPluginAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Plugin provider for <b>asciidocor.jvm.convert</b> with plugin id <b>org.asciidoctor.jvm.convert</b> and
         * with version reference <b>asciidoctor</b>
         * <p>
         * This plugin was declared in catalog libs.versions.toml
         */
        public Provider<PluginDependency> getConvert() { return createPlugin("asciidocor.jvm.convert"); }

    }

    public static class DependencyPluginAccessors extends PluginFactory {
        private final DependencyLicensePluginAccessors paccForDependencyLicensePluginAccessors = new DependencyLicensePluginAccessors(providers, config);

        public DependencyPluginAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Group of plugins at <b>plugins.dependency.license</b>
         */
        public DependencyLicensePluginAccessors getLicense() {
            return paccForDependencyLicensePluginAccessors;
        }

    }

    public static class DependencyLicensePluginAccessors extends PluginFactory {

        public DependencyLicensePluginAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Plugin provider for <b>dependency.license.report</b> with plugin id <b>com.github.jk1.dependency-license-report</b> and
         * with version reference <b>dependency.license.report</b>
         * <p>
         * This plugin was declared in catalog libs.versions.toml
         */
        public Provider<PluginDependency> getReport() { return createPlugin("dependency.license.report"); }

    }

    public static class FreefairPluginAccessors extends PluginFactory {

        public FreefairPluginAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Plugin provider for <b>freefair.lombok</b> with plugin id <b>io.freefair.lombok</b> and
         * with version reference <b>freefair.lombok</b>
         * <p>
         * This plugin was declared in catalog libs.versions.toml
         */
        public Provider<PluginDependency> getLombok() { return createPlugin("freefair.lombok"); }

    }

    public static class GradlePluginAccessors extends PluginFactory {
        private final GradleNexusPluginAccessors paccForGradleNexusPluginAccessors = new GradleNexusPluginAccessors(providers, config);

        public GradlePluginAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Group of plugins at <b>plugins.gradle.nexus</b>
         */
        public GradleNexusPluginAccessors getNexus() {
            return paccForGradleNexusPluginAccessors;
        }

    }

    public static class GradleNexusPluginAccessors extends PluginFactory {
        private final GradleNexusPublishPluginAccessors paccForGradleNexusPublishPluginAccessors = new GradleNexusPublishPluginAccessors(providers, config);

        public GradleNexusPluginAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Group of plugins at <b>plugins.gradle.nexus.publish</b>
         */
        public GradleNexusPublishPluginAccessors getPublish() {
            return paccForGradleNexusPublishPluginAccessors;
        }

    }

    public static class GradleNexusPublishPluginAccessors extends PluginFactory {

        public GradleNexusPublishPluginAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Plugin provider for <b>gradle.nexus.publish.plugin</b> with plugin id <b>io.github.gradle-nexus.publish-plugin</b> and
         * with version reference <b>gradle.nexus.publish.plugin</b>
         * <p>
         * This plugin was declared in catalog libs.versions.toml
         */
        public Provider<PluginDependency> getPlugin() { return createPlugin("gradle.nexus.publish.plugin"); }

    }

    public static class HidetakePluginAccessors extends PluginFactory {
        private final HidetakeSwaggerPluginAccessors paccForHidetakeSwaggerPluginAccessors = new HidetakeSwaggerPluginAccessors(providers, config);

        public HidetakePluginAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Group of plugins at <b>plugins.hidetake.swagger</b>
         */
        public HidetakeSwaggerPluginAccessors getSwagger() {
            return paccForHidetakeSwaggerPluginAccessors;
        }

    }

    public static class HidetakeSwaggerPluginAccessors extends PluginFactory {

        public HidetakeSwaggerPluginAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Plugin provider for <b>hidetake.swagger.generator</b> with plugin id <b>org.hidetake.swagger.generator</b> and
         * with version reference <b>swagger.generator</b>
         * <p>
         * This plugin was declared in catalog libs.versions.toml
         */
        public Provider<PluginDependency> getGenerator() { return createPlugin("hidetake.swagger.generator"); }

    }

    public static class OpenapiPluginAccessors extends PluginFactory {

        public OpenapiPluginAccessors(ProviderFactory providers, DefaultVersionCatalog config) { super(providers, config); }

        /**
         * Plugin provider for <b>openapi.generator</b> with plugin id <b>org.openapi.generator</b> and
         * with version reference <b>openapi.generator</b>
         * <p>
         * This plugin was declared in catalog libs.versions.toml
         */
        public Provider<PluginDependency> getGenerator() { return createPlugin("openapi.generator"); }

    }

}
